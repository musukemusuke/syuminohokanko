import discord
import traceback
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

# ====================== 共通パーサー ======================
def _parse_log(content: str) -> Dict[str, str]:
    """ログデータを安全にパースする共通関数"""
    data = {}
    for line in content.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        # URL内の「:」を巻き込まないよう、最初の「:」だけで分割
        key, value = line.split(":", 1)
        
        # 【超重要】前後にある余計な空白文字や特殊文字を完全に排除する
        key = key.strip().replace(" ", "").replace("　", "")
        value = value.strip()

        # 余計な引用符・括弧・非表示の空白文字をループで徹底的に除去
        for c in ['"', "'", "[", "]", " ", "　"]:
            while value.startswith(c) and value.endswith(c) and len(value) > 1:
                value = value[1:-1].strip()
        
        data[key] = value
    return data


# ====================== メイン関数 ======================
async def build_archive_embed(bot, channel_id: int, user_id: int, display_name: str):
    storage_channel = bot.get_channel(channel_id)
    if not storage_channel:
        return None

    folders: List[str] = []
    folder_rep: Dict[str, str] = {}      # フォルダ作成時の代表URL
    archive_data: Dict[str, List[str]] = {}  # {folder: [urls...]}

    try:
        async for msg in storage_channel.history(limit=1500):
            content = msg.content.strip()
            if not content:
                continue
            parsed = _parse_log(content)

            # 新規フォルダ作成
            if "NEW_FOLDER" in content:
                f_name = parsed.get("NEW_FOLDER")
                u_id = parsed.get("USER")
                link = parsed.get("LINK")

                if f_name and u_id and int(u_id) == user_id and f_name not in folders:
                    folders.append(f_name)
                    if link:
                        folder_rep[f_name] = link
                    archive_data.setdefault(f_name, [])

            # 実際の保存データ
            elif "FOLDER" in content:
                f_name = parsed.get("FOLDER")
                u_id = parsed.get("USER")
                link = parsed.get("LINK")

                if f_name and u_id and int(u_id) == user_id and link:
                    archive_data.setdefault(f_name, [])
                    if link not in archive_data[f_name]:
                        archive_data[f_name].append(link)

    except Exception:
        traceback.print_exc()
        return None

    if not folders:
        return None

    embed = discord.Embed(
        title=f"📚 {display_name} の趣味の保管庫",
        description="保存したリンク一覧（新しいフォルダ順）",
        color=0x2f3136
    )

    for folder in reversed(folders):
        urls = archive_data.get(folder, [])
        lines = []

        if folder in folder_rep:
            lines.append(f"⭐ **代表リンク:** {folder_rep[folder]}")
            if urls:
                lines.append("")

        lines.extend(urls)

        value = "\n".join(lines) if lines else "（まだ何も保存されていません）"
        
        # Embed制限対策
        if len(value) > 1000:
            value = value[:997] + "..."

        embed.add_field(name=f"📂 {folder}", value=value, inline=False)

    return embed


async def search_archive_data(bot, channel_id: int, user_id: int, keyword: str):
    storage_channel = bot.get_channel(channel_id)
    search_keyword = keyword.strip().lower()
    
    embed = discord.Embed(title=f'🔍 「{keyword}」の検索結果', color=0xd4af37)

    if not storage_channel:
        embed.description = "❌ データ金庫にアクセスできません。"
        return embed

    results = []
    count = 0

    try:
        async for msg in storage_channel.history(limit=1500):
            content = msg.content.strip()
            if "FOLDER" not in content and "NEW_FOLDER" not in content:
                continue

            parsed = _parse_log(content)
            
            f_name = parsed.get("FOLDER") or parsed.get("NEW_FOLDER")
            u_id = parsed.get("USER")
            link = parsed.get("LINK")

            if not u_id or str(u_id) != str(user_id) or not f_name:
                continue

            clean_f_name = f_name.strip().lower()
            clean_link = link.strip().lower() if link else ""

            if search_keyword in clean_f_name or (link and search_keyword in clean_link):
                if "NEW_FOLDER" in content:
                    results.append(f"📂 **{f_name}** (フォルダ)\n└ ⭐ 代表リンク: {link or 'なし'}")
                else:
                    results.append(f"📂 **{f_name}**\n└ {link}")
                
                count += 1
                if count >= 20:
                    break

    except Exception:
        traceback.print_exc()

    if not results:
        embed.description = "該当するデータが見つかりませんでした。"
        embed.color = 0x555555
    else:
        embed.description = f"{count}件見つかりました。\n\n" + "\n\n".join(results)

    return embed


async def delete_category_logs(bot, channel_id: int, user_id: int, folder_name: str) -> bool:
    storage_channel = bot.get_channel(channel_id)
    if not storage_channel:
        return False

    to_delete_bulk = []
    to_delete_single = []
    
    # 14日制限の基準時間を計算
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(days=14)

    # 判定ミスのブレをなくすため比較対象のフォルダ名をクリーンにする
    target_folder = folder_name.strip()

    try:
        async for msg in storage_channel.history(limit=1500):
            content = msg.content.strip()
            if "NEW_FOLDER" not in content and "FOLDER" not in content:
                continue

            parsed = _parse_log(content)
            f_name = parsed.get("NEW_FOLDER") or parsed.get("FOLDER")
            u_id = parsed.get("USER")

            # 【重要修正】IDとフォルダ名の前後の空白を完全に削ってから安全に比較する
            if f_name and u_id and f_name.strip() == target_folder and int(u_id) == user_id:
                if msg.created_at > limit_time:
                    to_delete_bulk.append(msg)
                else:
                    to_delete_single.append(msg)

        if not to_delete_bulk and not to_delete_single:
            return False

        # 14日以内のメッセージを一括削除
        if to_delete_bulk:
            for i in range(0, len(to_delete_bulk), 100):
                batch = to_delete_bulk[i:i + 100]
                if len(batch) == 1:
                    await batch.delete()
                else:
                    await storage_channel.delete_messages(batch)
                await asyncio.sleep(0.3)

        # 14日以上前のメッセージを1件ずつ削除
        if to_delete_single:
            for msg in to_delete_single:
                try:
                    await msg.delete()
                    await asyncio.sleep(0.2)
                except discord.NotFound:
                    pass

        return True

    except Exception as e:
        print(f"[delete_category_logs] Error: {e}")
        traceback.print_exc()
        return False

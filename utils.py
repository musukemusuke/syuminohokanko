import discord
import traceback
import asyncio
from typing import Dict, List, Optional


# ====================== 共通パーサー ======================
def _parse_log(content: str) -> Dict[str, str]:
    """VCログを安全にパースする共通関数"""
    data = {}
    for line in content.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # 余計な引用符・括弧を除去
        for c in ['"', "'", "[", "]"]:
            if value.startswith(c) and value.endswith(c):
                value = value[1:-1].strip()
        
        data[key] = value
    return data


# ====================== メイン関数 ======================
async def build_archive_embed(bot, vc_id: int, user_id: int, display_name: str):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders: List[str] = []
    folder_rep: Dict[str, str] = {}      # フォルダ作成時の代表URL
    archive_data: Dict[str, List[str]] = {}  # {folder: [urls...]}

    try:
        async for msg in storage_vc.history(limit=1500):
            content = msg.content.strip()
            if not content:
                continue
            parsed = _parse_log(content)

            # 新規フォルダ作成
            if "NEW_FOLDER" in content:
                f_name = parsed.get("NEW_FOLDER")
                u_id = int(parsed.get("USER", 0))
                link = parsed.get("LINK")

                if f_name and u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    if link:
                        folder_rep[f_name] = link
                    archive_data.setdefault(f_name, [])

            # 実際の保存データ
            elif "FOLDER" in content:
                f_name = parsed.get("FOLDER")
                u_id = int(parsed.get("USER", 0))
                link = parsed.get("LINK")

                if f_name and u_id == user_id and link:
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


async def search_archive_data(bot, vc_id: int, user_id: int, keyword: str):
    storage_vc = bot.get_channel(vc_id)
    embed = discord.Embed(title=f'🔍 「{keyword}」の検索結果', color=0xd4af37)

    if not storage_vc:
        embed.description = "❌ データ金庫にアクセスできません。"
        return embed

    results = []
    count = 0

    try:
        async for msg in storage_vc.history(limit=1200):
            if "FOLDER" not in msg.content:
                continue

            parsed = _parse_log(msg.content)
            f_name = parsed.get("FOLDER")
            u_id = int(parsed.get("USER", 0))
            link = parsed.get("LINK")

            if u_id != user_id or not f_name or not link:
                continue

            if keyword.lower() in f_name.lower() or keyword.lower() in link.lower():
                results.append(f"**{f_name}**\n└ {link}")
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


async def delete_category_logs(bot, vc_id: int, user_id: int, folder_name: str) -> bool:
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return False

    to_delete = []

    try:
        async for msg in storage_vc.history(limit=1500):
            parsed = _parse_log(msg.content)
            f_name = parsed.get("NEW_FOLDER") or parsed.get("FOLDER")
            u_id = int(parsed.get("USER", 0))

            if f_name == folder_name and u_id == user_id:
                to_delete.append(msg)

        if not to_delete:
            return False

        # 一括削除（効率的）
        for i in range(0, len(to_delete), 100):
            batch = to_delete[i:i + 100]
            if len(batch) == 1:
                await batch[0].delete()
            else:
                await storage_vc.delete_messages(batch)
            await asyncio.sleep(0.3)

        return True

    except Exception as e:
        print(f"[delete_category_logs] Error: {e}")
        traceback.print_exc()
        return False

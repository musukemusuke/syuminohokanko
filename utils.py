import discord
import traceback
import asyncio
from typing import Dict, List, Optional, Tuple


# ====================== 共通ヘルパー ======================
def _parse_log_message(content: str) -> Dict[str, str]:
    """VCのログメッセージをパースする共通関数"""
    data = {}
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue
            
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        
        # 余計な引用符・括弧を除去
        for char in ["'", '"', "[", "]"]:
            if value.startswith(char) and value.endswith(char):
                value = value[1:-1].strip()
        
        data[key] = value
    
    return data


# ====================== メイン関数 ======================
async def build_archive_embed(bot, vc_id: int, user_id: int, display_name: str):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders: List[str] = []
    folder_representative: Dict[str, str] = {}      # フォルダ作成時の代表URL
    archive_data: Dict[str, List[str]] = {}         # {folder: [urls]}

    try:
        async for msg in storage_vc.history(limit=1200):
            content = msg.content.strip()
            if not content:
                continue

            parsed = _parse_log_message(content)

            if "NEW_FOLDER" in content:   # 🆕NEW_FOLDER:
                f_name = parsed.get("NEW_FOLDER")
                u_id = int(parsed.get("USER", 0))
                link = parsed.get("LINK")

                if f_name and u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    if link:
                        folder_representative[f_name] = link
                    archive_data.setdefault(f_name, [])

            elif "FOLDER" in content:     # 📁FOLDER:
                f_name = parsed.get("FOLDER")
                u_id = int(parsed.get("USER", 0))
                link = parsed.get("LINK")

                if f_name and u_id == user_id and link:
                    archive_data.setdefault(f_name, [])
                    if link not in archive_data[f_name]:
                        archive_data[f_name].append(link)

    except Exception as e:
        traceback.print_exc()
        return None

    if not folders:
        return None

    embed = discord.Embed(
        title=f"📚 {display_name} の趣味の保管庫",
        description="保存したURL一覧です（最新順）",
        color=0x2f3136
    )

    # 新しいフォルダが上に来るように
    for folder in reversed(folders):
        urls = archive_data.get(folder, [])
        lines = []

        # 代表URL（フォルダ作成時のURL）
        if folder in folder_representative:
            lines.append(f"⭐ **代表**: {folder_representative[folder]}")
            if urls:
                lines.append("")

        # 保存されたURL一覧
        for url in urls:
            lines.append(url)

        value = "\n".join(lines) if lines else "（空のフォルダ）"
        
        # Embedのvalueは1024文字制限に注意
        if len(value) > 1000:
            value = value[:997] + "..."

        embed.add_field(name=f"📂 {folder}", value=value, inline=False)

    return embed


async def search_archive_data(bot, vc_id: int, user_id: int, keyword: str):
    storage_vc = bot.get_channel(vc_id)
    embed = discord.Embed(title=f"🔍 「{keyword}」の検索結果", color=0xd4af37)

    if not storage_vc:
        embed.description = "❌ データ金庫にアクセスできません。"
        return embed

    results = []
    found = 0

    try:
        async for msg in storage_vc.history(limit=1000):
            if "FOLDER" not in msg.content:
                continue

            parsed = _parse_log_message(msg.content)
            f_name = parsed.get("FOLDER")
            u_id_str = parsed.get("USER")
            link = parsed.get("LINK")

            if not (f_name and u_id_str and link):
                continue

            if int(u_id_str) != user_id:
                continue

            if keyword.lower() in f_name.lower() or keyword.lower() in link.lower():
                results.append(f"**{f_name}**\n└ {link}")
                found += 1
                if found >= 20:      # 結果を多すぎないように制限
                    break

    except Exception:
        traceback.print_exc()

    if not results:
        embed.description = "該当するデータは見つかりませんでした。"
        embed.color = 0x555555
    else:
        embed.description = f"{found}件見つかりました。\n\n" + "\n\n".join(results)

    return embed


async def delete_category_logs(bot, vc_id: int, user_id: int, folder_name: str) -> bool:
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return False

    to_delete = []

    try:
        async for msg in storage_vc.history(limit=1200):
            parsed = _parse_log_message(msg.content)

            f_name = parsed.get("NEW_FOLDER") or parsed.get("FOLDER")
            u_id_str = parsed.get("USER")

            if f_name == folder_name and u_id_str and int(u_id_str) == user_id:
                to_delete.append(msg)

        if not to_delete:
            return False

        # 一括削除（可能な限り）
        if len(to_delete) == 1:
            await to_delete[0].delete()
        else:
            # 100件まで一括削除可能
            for i in range(0, len(to_delete), 100):
                batch = to_delete[i:i+100]
                await storage_vc.delete_messages(batch)
                await asyncio.sleep(0.3)  # 安全マージン

        return True

    except Exception as e:
        print(f"[delete_category_logs] Error: {e}")
        traceback.print_exc()
        return False

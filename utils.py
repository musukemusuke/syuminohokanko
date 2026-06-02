import discord
import traceback
import asyncio
from typing import Dict, List, Union
from datetime import datetime, timedelta, timezone

def _parse_log(content: str) -> Dict[str, str]:
    data = {}
    for line in content.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        
        key = key.strip().replace(" ", "").replace("　", "")
        value = value.strip()

        for c in ['"', "'", "[", "]", " ", "　"]:
            while value.startswith(c) and value.endswith(c) and len(value) > 1:
                value = value[1:-1].strip()
        
        data[key] = value
    return data


async def build_archive_embed(bot, target_loc: Union[discord.TextChannel, discord.Thread], user_id: int, display_name: str):
    if not target_loc:
        return None

    folders: List[str] = []
    folder_rep: Dict[str, str] = {}      
    archive_data: Dict[str, List[str]] = {}  

    try:
        async for msg in target_loc.history(limit=1500):
            content = msg.content.strip()
            if not content:
                continue
            parsed = _parse_log(content)

            if "NEW_FOLDER" in content:
                f_name = parsed.get("NEW_FOLDER")
                u_id = parsed.get("USER")
                link = parsed.get("LINK")

                if f_name and u_id and int(u_id) == user_id and f_name not in folders:
                    folders.append(f_name)
                    if link:
                        folder_rep[f_name] = link
                    archive_data.setdefault(f_name, [])

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
        
        if len(value) > 1000:
            value = value[:997] + "..."

        embed.add_field(name=f"📂 {folder}", value=value, inline=False)

    return embed


async def search_archive_data(bot, target_loc: Union[discord.TextChannel, discord.Thread], user_id: int, keyword: str):
    if not target_loc:
        return discord.Embed(description="❌ 対象のスレッドが見つかりません。", color=0x555555)
        
    search_keyword = keyword.strip().lower()
    embed = discord.Embed(title=f'🔍 「{keyword}」の検索結果', color=0xd4af37)
    results = []
    count = 0

    try:
        async for msg in target_loc.history(limit=1500):
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


async def delete_category_logs(bot, target_loc: Union[discord.TextChannel, discord.Thread], user_id: int, folder_name: str) -> bool:
    if not target_loc:
        return False

    to_delete_bulk = []
    to_delete_single = []
    
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(days=14)
    target_folder = folder_name.strip()

    try:
        async for msg in target_loc.history(limit=1500):
            content = msg.content.strip()
            if "NEW_FOLDER" not in content and "FOLDER" not in content:
                continue

            parsed = _parse_log(content)
            f_name = parsed.get("NEW_FOLDER") or parsed.get("FOLDER")
            u_id = parsed.get("USER")

            if f_name and u_id and f_name.strip() == target_folder and int(u_id) == user_id:
                if msg.created_at > limit_time:
                    to_delete_bulk.append(msg)
                else:
                    to_delete_single.append(msg)

        if not to_delete_bulk and not to_delete_single:
            return False

        if to_delete_bulk:
            for msg in to_delete_bulk:
                try:
                    await msg.delete()
                    await asyncio.sleep(0.1)
                except discord.NotFound:
                    pass

        if to_delete_single:
            for msg in to_delete_single:
                try:
                    await msg.delete()
                    await asyncio.sleep(0.1)
                except discord.NotFound:
                    pass

        return True

    except Exception as e:
        print(f"[delete_category_logs] Error: {e}")
        traceback.print_exc()
        return False

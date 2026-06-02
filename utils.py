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
        # 【改善】キーと値の周りにあるスペースや特殊文字を完全にそぎ落とす
        key = key.strip()
        value = value.strip()

        # 余計な引用符・括弧を除去
        for c in ['"', "'", "[", "]", " ", "　"]:
            if value.startswith(c) and value.endswith(c):
                value = value[1:-1].strip()
        
        data[key] = value
    return data

# ====================== メイン関数 ======================

# (build_archive_embed や delete_category_logs はそのまま)

async def search_archive_data(bot, channel_id: int, user_id: int, keyword: str):
    storage_channel = bot.get_channel(channel_id)
    # 【改善】検索キーワードの前後の余計なスペースを消し、小文字に統一
    search_keyword = keyword.strip().lower()
    
    embed = discord.Embed(title=f'🔍 「{keyword}」の検索結果', color=0xd4af37)

    if not storage_channel:
        embed.description = "❌ データ金庫にアクセスできません。"
        return embed

    results = []
    count = 0

    try:
        # 過去ログを遡る（上限1500件程度に調整）
        async for msg in storage_channel.history(limit=1500):
            content = msg.content.strip()
            if "FOLDER" not in content:
                continue

            parsed = _parse_log(content)
            f_name = parsed.get("FOLDER")
            u_id = parsed.get("USER")
            link = parsed.get("LINK")

            # IDの比較を確実に行う（文字列どうしで比較）
            if not u_id or str(u_id) != str(user_id) or not f_name or not link:
                continue

            # 【改善】フォルダ名とリンクも前後のスペースを除去し、小文字にして部分一致判定
            clean_f_name = f_name.strip().lower()
            clean_link = link.strip().lower()

            if search_keyword in clean_f_name or search_keyword in clean_link:
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

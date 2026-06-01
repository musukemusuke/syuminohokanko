import discord
from views import ArchiveViewButton

async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc: return None

    folders, archive_data = [], {}
    async for msg in storage_vc.history(limit=1000):
        content = msg.content
        lines = content.split("\n")
        if content.startswith("🆕NEW_FOLDER:"):
            try:
                f_name = lines[0].replace("🆕NEW_FOLDER:", "").strip()
                u_id = int(lines[1].replace("👤USER:", "").strip())
                if u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    archive_data[f_name] = []
            except: continue
        elif content.startswith("📁FOLDER:"):
            try:
                f_name = lines[0].replace("📁FOLDER:", "").strip()
                u_id = int(lines[1].replace("👤USER:", "").strip())
                data_url = lines[2].replace("🔗DATA:", "").strip()
                if u_id == user_id:
                    if f_name not in archive_data: archive_data[f_name] = []
                    if data_url not in archive_data[f_name]: archive_data[f_name].append(data_url)
            except: continue

    if not folders: return None
    embed = discord.Embed(title=f"📚 {display_name} の一覧", description="クリックで再生・閲覧可能。", color=discord.Color.blue())
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_list = "\n".join([f"• [データを見る]({item})" for item in items]) if items else "*（データなし）*"
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)
    return embed

async def check_and_restore_messages(bot, post_id, archive_id, build_embed_func):
    ch_post, ch_archive = bot.get_channel(post_id), bot.get_channel(archive_id)
    if ch_post:
        has_intro = False
        async for msg in ch_post.history(limit=20):
            if msg.author == bot.user and "ボットへようこそ" in msg.content:
                has_intro = True
                break
        if not has_intro:
            await ch_post.send("📌 **ボットへようこそ！**\n1. `/category_add` でフォルダを作ります。\n2. ここにURLや画像を貼ると仕分けメニューが出現します！")

    if ch_archive:
        has_button = False
        async for msg in ch_archive.history(limit=20):
            if msg.author == bot.user and msg.components:
                has_button = True
                break
        if not has_button:
            await ch_archive.send("ボタンを押すと、保存したデータ一覧を表示します。", view=ArchiveViewButton(build_embed_func))

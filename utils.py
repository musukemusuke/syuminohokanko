import discord


async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders = []
    archive_data = {}

    async for msg in storage_vc.history(limit=1000):
        content = msg.content
        if content.startswith("🆕NEW_FOLDER:"):
            try:
                f_name = (
                    content.split("🆕NEW_FOLDER:")
                    .split("\n👤USER:")
                    .strip()
                )
                u_id = int(content.split("👤USER:").strip())
                if u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    archive_data[f_name] = []
            except:
                continue
        elif content.startswith("📁FOLDER:"):
            try:
                f_name = (
                    content.split("📁FOLDER:").split("\n👤USER:")
                    .strip()
                )
                u_id = int(
                    content.split("👤USER:").split("\n🔗LINK:").strip()
                )
                link = content.split("🔗LINK:").strip()
                if u_id == user_id:
                    if f_name not in archive_data:
                        archive_data[f_name] = []
                    if link not in archive_data[f_name]:
                        archive_data[f_name].append(link)
            except:
                continue

    if not folders:
        return None

    embed = discord.Embed(
        title=f"📚 {display_name} のブックマーク一覧",
        description="リンク（青い文字）をクリックすると、保存した動画や画像のメッセージに直接ジャンプできます。",
        color=discord.Color.blue(),
    )
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_list = (
            "\n".join(
                [
                    f"• [保存したデータを見に行く（ここをクリック）]({item})"
                    for item in items
                ]
            )
            if items
            else "*（まだデータが登録されていません）*"
        )
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)

    return embed

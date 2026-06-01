import discord


async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders, archive_data = [], {}

    # 金庫VCの過去ログを正確に読み込んで集計（バグ修正）
    async for msg in storage_vc.history(limit=1000):
        content = msg.content

        if content.startswith("🆕NEW_FOLDER:"):
            try:
                # リスト化された中から、行番号[0]と[1]を狙い撃ちして文字を抽出
                lines = content.split("\n")
                f_name = lines[0].replace("🆕NEW_FOLDER:", "").strip()
                u_id = int(lines[1].replace("👤USER:", "").strip())

                if u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    archive_data[f_name] = []
            except:
                continue

        elif content.startswith("📁FOLDER:"):
            try:
                # リスト化された中から、行番号[0][1][2]を狙い撃ちして正確に抽出
                lines = content.split("\n")
                f_name = lines[0].replace("📁FOLDER:", "").strip()
                u_id = int(lines[1].replace("👤USER:", "").strip())
                data_url = lines[2].replace("🔗DATA:", "").strip()

                if u_id == user_id:
                    if f_name not in archive_data:
                        archive_data[f_name] = []
                    if data_url not in archive_data[f_name]:
                        archive_data[f_name].append(data_url)
            except:
                continue

    if not folders:
        return None

    embed = discord.Embed(
        title=f"📚 {display_name} の一覧",
        description=(
            "クリックで再生・閲覧可能。\n"
            "（元のチャットが消されても100%見られます）"
        ),
        color=discord.Color.blue(),
    )
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_list = (
            "\n".join([f"• [データを見る]({item})" for item in items])
            if items
            else "*（データなし）*"
        )
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)

    return embed

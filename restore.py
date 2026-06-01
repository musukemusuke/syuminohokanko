import discord


async def check_and_restore_messages(
    bot, post_id, archive_id, view_instance
):
    ch_post = bot.get_channel(post_id)
    ch_archive = bot.get_channel(archive_id)

    if ch_post:
        has_intro = False
        async for msg in ch_post.history(limit=20):
            if (
                msg.author == bot.user
                and "ブックマーク・アーカイブボットへようこそ"
                in msg.content
            ):
                has_intro = True
                break
        if not has_intro:
            await ch_post.send(
                "📌 **ブックマーク・アーカイブボットへようこそ！**\n1. まずは `/category_add` コマンドで、好きなフォルダを作ってください。\n2. その後、このチャンネルに動画URLや画像を貼り付けると、自動で仕分けメニューが出現します！"
            )

    if ch_archive:
        has_button = False
        async for msg in ch_archive.history(limit=20):
            if msg.author == bot.user and msg.components:
                has_button = True
                break
        if not has_button:
            await ch_archive.send(
                "以下のボタンを押すと、あなたが保存した趣味のデータ一覧を本人にだけ見える形で表示します。",
                view=view_instance,
            )

import discord


async def check_and_restore_messages(
    bot, post_id, archive_id, view_class
):
    """案内文やボタンが消されていたら自動で再生成する関数"""
    ch_post = bot.get_channel(post_id)
    ch_archive = bot.get_channel(archive_id)

    if ch_post:
        has_intro = False
        async for msg in ch_post.history(limit=20):
            if (
                msg.author == bot.user
                and "ブックマークボットへようこそ"
                in msg.content
            ):
                has_intro = True
                break
        if not has_intro:
            await ch_post.send(
                "📌 **ブックマークボットへようこそ！**\n"
                "1. `/category_add` で"
                "フォルダを作ります。\n"
                "2. ここにURLや画像を貼ると、"
                "仕分けメニューが出現します！"
            )

    if ch_archive:
        has_button = False
        async for msg in ch_archive.history(limit=20):
            if (
                msg.author == bot.user
                and msg.components
            ):
                has_button = True
                break
        if not has_button:
            await ch_archive.send(
                "ボタンを押すと、"
                "あなたが保存したデータ一覧を"
                "表示します。",
                view=view_class,
            )

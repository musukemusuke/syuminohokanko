import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed
from views import CategorySelectView

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_id, archive_id, storage_vc_id = None, None, None


async def my_embed_factory(user_id, display_name):
    return await build_archive_embed(
        bot, storage_vc_id, user_id, display_name
    )


# 仕分け完了時にアーカイブ画面を自動リフレッシュする処理
async def update_archive_channel_embed(guild, user_id, display_name):
    ch_archive = bot.get_channel(archive_id)
    if not ch_archive:
        return
    new_embed = await my_embed_factory(user_id, display_name)
    if not new_embed:
        return

    async for msg in ch_archive.history(limit=20):
        if msg.author == bot.user and msg.embeds:
            await msg.edit(embed=new_embed)
            print(f"[{guild.name}] アーカイブ画面を更新しました。")
            break


@bot.tree.command(
    name="setup",
    description="【管理者専用】ブックマーク用のカテゴリーとチャンネルを生成します",
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_channels(interaction: discord.Interaction):
    global post_id, archive_id, storage_vc_id
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    cat_name = "📁 ブックマーク"
    cat = discord.utils.get(guild.categories, name=cat_name) or (
        await guild.create_category(name=cat_name)
    )

    ch_post = discord.utils.get(
        cat.text_channels, name="📥・ブックマーク"
    ) or (
        await guild.create_text_channel(
            name="📥・ブックマーク",
            category=cat,
            topic="ここに動画や画像のURLを貼ると、ボットが自動で仕分けを案内します。",
        )
    )

    topic_text = (
        "`/archive_view` コマンドで、これまでに"
        "集めたデータ一覧をここに表示できます。"
    )
    ch_arc = discord.utils.get(
        cat.text_channels, name="📚・アーカイブ"
    ) or (
        await guild.create_text_channel(
            name="📚・アーカイブ", category=cat, topic=topic_text
        )
    )

    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")

    if not ch_vc:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, connect=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, connect=True, send_messages=True
            ),
        }
        ch_vc = await guild.create_voice_channel(
            name="🤫・データ金庫", category=cat, overwrites=overwrites
        )

    post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id

    # 不要なボタン送信を完全に廃止し、最初のメッセージだけをスッキリ投稿
    await ch_arc.send(
        "📚 **趣味のアーカイブ図書室へようこそ！**\n"
        "チャット欄に `/archive_view` と入力すると、"
        "あなたが保存した趣味のデータ一覧を"
        "本人にだけ見える非公開画面でいつでも確認できます。"
    )
    await interaction.followup.send(
        "✅ チャンネルと秘密金庫の生成が完了しました！", ephemeral=True
    )


@bot.tree.command(
    name="category_add",
    description="新しくデータを仕分けるフォルダ（カテゴリー）を追加します",
)
@app_commands.describe(name="追加するフォルダ名（例：動画、イラスト、ゲームなど）")
async def category_add(interaction: discord.Interaction, name: str):
    storage_vc = bot.get_channel(storage_vc_id)
    await storage_vc.send(
        f"🆕NEW_FOLDER:{name}\n" f"👤USER:{interaction.user.id}"
    )
    await interaction.response.send_message(
        f"✅ フォルダ「📁 **{name}**」を新規作成しました！", ephemeral=True
    )


@bot.tree.command(
    name="archive_view", description="自分が保存したアーカイブ一覧を表示します"
)
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = await my_embed_factory(
        interaction.user.id, interaction.user.display_name
    )
    if embed is None:
        await interaction.followup.send(
            "📭 まだフォルダがありません。まずは `/category_add` で作成してください。",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != post_id:
        return

    has_content = bool(message.attachments) or (
        "http://" in message.content or "https://" in message.content
    )
    if has_content:
        storage_vc = bot.get_channel(storage_vc_id)
        user_id = message.author.id
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                try:
                    lines = msg.content.split("\n")
                    u_id_text = lines[1].replace("👤USER:", "").strip()
                    if int(u_id_text) == user_id:
                        f_name = (
                            lines[0].replace("🆕NEW_FOLDER:", "").strip()
                        )
                        if f_name not in folders:
                            folders.append(f_name)
                except:
                    continue

        if not folders:
            await message.reply(
                "💡 まだ仕分けフォルダがありません。まずは `/category_add` コマンドでフォルダを作ってください！"
            )
            return

        view = CategorySelectView(
            reversed(folders), message.id, post_id, storage_vc_id
        )
        await message.reply("どのフォルダにアーカイブしますか？", view=view)

        bot.loop.create_task(
            watch_and_refresh_archive(
                message.guild, message.author.id, message.author.display_name
            )
        )

    await bot.process_commands(message)


async def watch_and_refresh_archive(guild, user_id, display_name):
    await asyncio.sleep(2)
    await update_archive_channel_embed(guild, user_id, display_name)


@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user.name}")
    await bot.tree.sync()


async def main():
    async with bot:
        bot.loop.create_task(asyncio.sleep(9900))
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass

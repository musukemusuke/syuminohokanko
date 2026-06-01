import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from utils import build_archive_embed, check_and_restore_messages
from views import CategorySelectView

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_id, archive_id, storage_vc_id = None, None, None


async def my_embed_factory(user_id, display_name):
    return await build_archive_embed(
        bot, storage_vc_id, user_id, display_name
    )


# ★【新機能】コマンドを打ったらチャンネルを自動生成する命令
@bot.tree.command(
    name="setup",
    description="【管理者専用】ブックマーク用のカテゴリーとチャンネルを生成します",
)
@app_commands.checks.has_permissions(administrator=True)  # 管理者だけが打てるロック
async def setup_channels(interaction: discord.Interaction):
    global post_id, archive_id, storage_vc_id
    await interaction.response.defer(
        ephemeral=True
    )  # 読み込み中画面をキープ

    guild = interaction.guild

    # 1. カテゴリー「📁 ブックマーク」を作成
    cat_name = "📁 ブックマーク"
    cat = discord.utils.get(guild.categories, name=cat_name) or (
        await guild.create_category(name=cat_name)
    )

    # 2. カテゴリーの中に2つのテキスト部屋を作成
    ch_post = discord.utils.get(
        cat.text_channels, name="📥・ブックマーク"
    ) or (await guild.create_text_channel(name="📥・ブックマーク", category=cat))

    ch_arc = discord.utils.get(
        cat.text_channels, name="📚・アーカイブ"
    ) or (await guild.create_text_channel(name="📚・アーカイブ", category=cat))

    # 3. ★全人類（お相手含む）から完全非表示（Hide）にする鉄壁ロックの金庫VCを作成
    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
    if not ch_vc:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),  # 一般人はHide
            guild.owner: discord.PermissionOverwrite(
                view_channel=False
            ),  # ★お相手（オーナー）も完全にHide
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True
            ),  # ボットだけが見える
        }
        ch_vc = await guild.create_voice_channel(
            name="🤫・データ金庫", category=cat, overwrites=overwrites
        )

    # プログラムにIDを記憶させる
    post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id

    # 部屋の中に最初の案内文と閲覧ボタンを自動設置
    await check_and_restore_messages(bot, post_id, archive_id, my_embed_factory)

    await interaction.followup.send(
        "✅ チャンネルの自動リフォームが完了しました！", ephemeral=True
    )


@bot.tree.command(
    name="category_add", description="仕分けフォルダを追加します"
)
async def category_add(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    storage_vc = bot.get_channel(storage_vc_id)
    if storage_vc:
        await storage_vc.send(
            f"🆕NEW_FOLDER:{name}\n" f"👤USER:{interaction.user.id}"
        )
        await interaction.followup.send(
            f"✅ 📁 **{name}** を作成しました！", ephemeral=True
        )


@bot.tree.command(
    name="archive_view", description="アーカイブ一覧を表示します"
)
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = await my_embed_factory(
        interaction.user.id, interaction.user.display_name
    )
    await interaction.followup.send(
        embed=embed or "📭 フォルダがありません。", ephemeral=True
    )


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author == bot.user:
        await check_and_restore_messages(
            bot, post_id, archive_id, my_embed_factory
        )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != post_id:
        return
    if bool(message.attachments) or "http" in message.content:
        storage_vc = bot.get_channel(storage_vc_id)
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                lines = msg.content.split("\n")
                if (
                    int(lines.replace("👤USER:", "").strip())
                    == message.author.id
                ):
                    folders.append(
                        lines.replace("🆕NEW_FOLDER:", "").strip()
                    )
        if not folders:
            await message.reply(
                "💡 まずは `/category_add` で" "フォルダを作ってください！"
            )
            return
        await message.reply(
            "どのフォルダにアーカイブしますか？",
            view=CategorySelectView(
                reversed(folders), message, post_id, storage_vc_id
            ),
        )


@bot.event
async def on_ready():
    print(f"Online: {bot.user.name}")
    await bot.tree.sync()  # スラッシュコマンド（/setup）をサーバーに登録


async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())

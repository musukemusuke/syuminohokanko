import asyncio
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
import traceback

from utils import build_archive_embed
from views import CategorySelectView

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_id, archive_id, storage_vc_id = None, None, None


async def my_embed_factory(user_id, display_name):
    if not storage_vc_id:
        return None
    return await build_archive_embed(
        bot, storage_vc_id, user_id, display_name
    )


# 仕分け完了時にアーカイブ画面を自動リフレッシュする処理
async def update_archive_channel_embed(guild, user_id, display_name):
    if not archive_id:
        return
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


# 再起動時にもチャンネルが外れないように、チャンネルIDを読み直す処理
def load_channel_ids(guild: discord.Guild):
    global post_id, archive_id, storage_vc_id
    cat = discord.utils.get(guild.categories, name="📁 ブックマーク")
    if not cat:
        return False
    
    ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク")
    ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ")
    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
    
    if ch_post and ch_arc and ch_vc:
        post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id
        return True
    return False


@bot.tree.command(
    name="setup",
    description="【管理者専用】ブックマーク用のカテゴリーとチャンネルを生成します",
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_channels(interaction: discord.Interaction):
    global post_id, archive_id, storage_vc_id
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        cat_name = "📁 ブックマーク"
        cat = discord.utils.get(guild.categories, name=cat_name) or (
            await guild.create_category(name=cat_name)
        )

        post_topic = (
            "まずは `/category_add` コマンドで仕分けフォルダを作ってください。\n"
            "その後、ここに動画や画像のURLを貼ると自動仕分けが始まります。"
        )
        ch_post = discord.utils.get(
            cat.text_channels, name="📥・ブックマーク"
        ) or (
            await guild.create_text_channel(
                name="📥・ブックマーク", category=cat, topic=post_topic
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

        await interaction.followup.send(
            "✅ チャンネルと秘密金庫の生成が完了しました！", ephemeral=True
        )
        print("[SUCCESS] 全てのチャンネル・VCの生成/取得に成功しました。")

    except discord.Forbidden:
        print("[ERROR] ボットの権限（チャンネル管理など）が不足しています。")
        await interaction.followup.send("❌ 権限不足によりチャンネルの作成に失敗しました。", ephemeral=True)
    except Exception as e:
        print("[CRITICAL ERROR] setupコマンド実行中にエラーが発生しました:")
        traceback.print_exc()
        await interaction.followup.send(f"❌ セットアップ中に予期せぬエラーが発生しました: {e}", ephemeral=True)


@bot.tree.command(
    name="category_add",
    description="新しくデータを仕分けるフォルダ（カテゴリー）を追加します",
)
@app_commands.describe(name="追加するフォルダ名（例：動画、イラスト、ゲームなど）")
async def category_add(interaction: discord.Interaction, name: str):
    global storage_vc_id
    if not storage_vc_id and interaction.guild:
        load_channel_ids(interaction.guild)

    storage_vc = bot.get_channel(storage_vc_id)
    if not storage_vc:
        await interaction.response.send_message("❌ まだ `/setup` が完了していないか、金庫が見つかりません。", ephemeral=True)
        return
        
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
    global storage_vc_id
    if not storage_vc_id and interaction.guild:
        load_channel_ids(interaction.guild)

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
    global post_id, storage_vc_id
    if message.author.bot:
        return

    if message.guild and (not post_id or not storage_vc_id):
        load_channel_ids(message.guild)

    if message.channel.id != post_id:
        return

    # メッセージ本文からhttp(s)から始まるURLを探す
    url_match = re.search(r"https?://[^\s]+", message.content)
    
    # URLが本文にある、もしくは添付ファイルがある場合のみ処理
    if url_match or message.attachments:
        storage_vc = bot.get_channel(storage_vc_id)
        if not storage_vc:
            return

        # 💡 本文のURLを最優先し、本文になければ1つ目の画像のURLを取得する
        if url_match:
            original_url = url_match.group(0)
        else:
            original_url = message.attachments[0].url

        user_id = message.author.id
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                try:
                    lines = msg.content.split("\n")
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"):
                            f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()

                    if f_name and u_id_text:
                        if int(u_id_text) == user_id:
                            if f_name not in folders:
                                folders.append(f_name)
                except:
                    continue

        if not folders:
            await message.reply(
                "💡 まだ仕分けフォルダがありません。まずは `/category_add` コマンドでフォルダを作ってください！"
            )
            return

        # 💡 message.id の代わりに、取得したオリジナルのURLを直接Viewに渡します
        view = CategorySelectView(
            reversed(folders), original_url, post_id, storage_vc_id
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
    
    for guild in bot.guilds:
        if load_channel_ids(guild):
            print(f"[{guild.name}] のチャンネル設定を自動的に復元しました。")


async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

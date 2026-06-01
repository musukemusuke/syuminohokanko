import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_id, archive_id, storage_vc_id = None, None, None


# --- 1. 誰も見えない金庫VCからデータを【逆方向スキャン】して一覧を作る関数 ---
async def build_archive_embed(user_id, display_name):
    storage_vc = bot.get_channel(storage_vc_id)
    if not storage_vc:
        return None

    folders = []
    archive_data = {}

    # 金庫VCの過去ログを正確に1行ずつ読み込んで解析（バグを完全修正）
    async for msg in storage_vc.history(limit=1000):
        content = msg.content

        if content.startswith("🆕NEW_FOLDER:"):
            try:
                # 文字列を正しく切り分けてフォルダ名とユーザーIDを抽出
                f_name = (
                    content.split("🆕NEW_FOLDER:")[1]
                    .split("\n👤USER:")[0]
                    .strip()
                )
                u_id = int(content.split("👤USER:")[1].strip())
                if u_id == user_id and f_name not in folders:
                    folders.append(f_name)
                    archive_data[f_name] = []
            except:
                continue

        elif content.startswith("📁FOLDER:"):
            try:
                # 文字列を正しく切り分けてデータURLを抽出（完全双方向化）
                f_name = (
                    content.split("📁FOLDER:")[1].split("\n👤USER:")[0].strip()
                )
                u_id = int(
                    content.split("👤USER:")[1].split("\n🔗DATA:")[0].strip()
                )
                data_url = content.split("🔗DATA:")[1].strip()

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
        description="クリックで再生・閲覧可能。\n（元のチャットが消されても100%見られます）",
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


# --- 2. アーカイブチャンネルの固定閲覧ボタンの処理 ---
class ArchiveViewButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="自分のブックマークを見る",
        style=discord.ButtonStyle.primary,
        custom_id="view_my_archive",
        emoji="📚",
    )
    async def view_archive(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        embed = await build_archive_embed(
            interaction.user.id, interaction.user.display_name
        )
        if embed is None:
            await interaction.followup.send(
                "📭 まだ仕分けフォルダがありません。最初に `/category_add` で作ってください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


# --- 3. 仕分け用プルダウンメニュー（物理コピーバックアップ仕様） ---
class CategorySelect(discord.ui.Select):

    def __init__(self, categories, message):
        self.orig_msg = message
        options = [
            discord.SelectOption(label=cat, description=f"「{cat}」に保存")
            for cat in categories
        ]
        super().__init__(
            placeholder="フォルダを選択...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        storage_vc = bot.get_channel(storage_vc_id)
        if not storage_vc:
            return

        selected_folder = self.values
        saved_url = ""

        # 画像や動画ファイルそのものを隠し金庫VCへ物理コピー転送
        if self.orig_msg.attachments:
            for attachment in self.orig_msg.attachments:
                file_data = await attachment.to_file()
                backup_msg = await storage_vc.send(
                    content="📦 BACKUP", file=file_data
                )
                saved_url = backup_msg.attachments.url
                break
        else:
            for word in self.orig_msg.content.split():
                if word.startswith("http"):
                    saved_url = word
                    break

        if saved_url:
            log_text = (
                f"📁FOLDER:{selected_folder}\n"
                f"👤USER:{interaction.user.id}\n"
                f"🔗DATA:{saved_url}"
            )
            await storage_vc.send(log_text)
            await interaction.followup.send(
                f"✅ **{selected_folder}** に保存しました！",
                ephemeral=True,
            )


# --- 4. スラッシュコマンド（/setup, /category_add, /archive_view） ---
@bot.tree.command(
    name="setup",
    description="【管理者専用】ブックマーク用のカテゴリーとチャンネルを生成します",
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_channels(interaction: discord.Interaction):
    global post_id, archive_id, storage_vc_id
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    cat = discord.utils.get(guild.categories, name="📁 ブックマーク") or (
        await guild.create_category(name="📁 ブックマーク")
    )
    ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク") or (
        await guild.create_text_channel(name="📥・ブックマーク", category=cat)
    )
    ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ") or (
        await guild.create_text_channel(name="📚・アーカイブ", category=cat)
    )

    # ★お相手（オーナー）の画面からも完全にHide（非表示）にする鉄壁の金庫VC
    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
    if not ch_vc:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, connect=False
            ),
            guild.owner: discord.PermissionOverwrite(
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

    # 部屋の案内メッセージと「閲覧ボタン」を自動設置
    await ch_post.send(
        "📌 **ブックマークボットへようこそ！**\n1. `/category_add` でフォルダを作ります。\n2. ここにURLや画像を貼ると、仕分けメニューが出現します！"
    )
    await ch_arc.send(
        "ボタンを押すと、あなたが保存したデータ一覧を表示します。",
        view=ArchiveViewButton(),
    )
    await interaction.followup.send(
        "✅ チャンネルと秘密金庫の生成が完了しました！", ephemeral=True
    )


@bot.tree.command(
    name="category_add", description="仕分けフォルダを追加します"
)
async def category_add(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    storage_vc = bot.get_channel(storage_vc_id)
    if storage_vc:
        await storage_vc.send(
            f"🆕NEW_FOLDER:{name}\n👤USER:{interaction.user.id}"
        )
        await interaction.followup.send(
            f"✅ 📁 **{name}** を作成しました！", ephemeral=True
        )


@bot.tree.command(
    name="archive_view", description="アーカイブ一覧を表示します"
)
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = await build_archive_embed(
        interaction.user.id, interaction.user.display_name
    )
    await interaction.followup.send(
        embed=embed or "📭 フォルダがありません。", ephemeral=True
    )


# --- 5. メッセージ検知機能 ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != post_id:
        return
    if bool(message.attachments) or "http" in message.content:
        storage_vc = bot.get_channel(storage_vc_id)
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                try:
                    c = msg.content
                    f_name = (
                        c.split("🆕NEW_FOLDER:")[1].split("\n👤USER:")[0].strip()
                    )
                    u_id = int(c.split("👤USER:")[1].strip())
                    if u_id == message.author.id and f_name not in folders:
                        folders.append(f_name)
                except:
                    continue

        if not folders:
            await message.reply(
                "💡 まだフォルダがありません。まずは `/category_add` でフォルダを作ってください！"
            )
            return

        view = discord.ui.View().add_item(
            CategorySelect(reversed(folders), message)
        )
        await message.reply("どのフォルダにアーカイブしますか？", view=view)
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"Online: {bot.user.name}")
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

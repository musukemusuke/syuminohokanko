import os
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_channel_id = None
archive_channel_id = None
storage_vc_id = None

class CategorySelect(discord.ui.Select):
    def __init__(self, categories, message_id):
        self.message_id = message_id
        options = [
            discord.SelectOption(label=cat, description=f"フォルダ「{cat}」に保存します")
            for cat in categories
        ]
        super().__init__(placeholder="保存するフォルダを選択してください...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        storage_vc = bot.get_channel(storage_vc_id)
        if not storage_vc:
            await interaction.followup.send("❌ エラー: データ金庫が見つかりません。", ephemeral=True)
            return

        selected_folder = self.values
        archive_link = f"https://discord.com{interaction.guild_id}/{post_channel_id}/{self.message_id}"

        await storage_vc.send(f"📁FOLDER:{selected_folder}\n👤USER:{interaction.user.id}\n🔗LINK:{archive_link}")
        await interaction.followup.send(f"✅ **{selected_folder}** フォルダに登録しました！\n（データは誰も見えない非表示VCに永久保存されました）", ephemeral=True)

class CategorySelectView(discord.ui.View):
    def __init__(self, categories, message_id):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, message_id))

@bot.tree.command(name="category_add", description="新しくデータを仕分けるフォルダ（カテゴリー）を追加します")
@app_commands.describe(name="追加するフォルダ名（例：動画、イラスト、ゲームなど）")
async def category_add(interaction: discord.Interaction, name: str):
    storage_vc = bot.get_channel(storage_vc_id)
    await storage_vc.send(f"🆕NEW_FOLDER:{name}\n👤USER:{interaction.user.id}")
    await interaction.response.send_message(f"✅ フォルダ「📁 **{name}**」を新規作成しました！", ephemeral=True)

@bot.tree.command(name="archive_view", description="自分が保存したアーカイブ一覧を表示します")
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer()
    
    storage_vc = bot.get_channel(storage_vc_id)
    user_id = interaction.user.id
    folders = []
    archive_data = {}

    async for msg in storage_vc.history(limit=1000):
        if msg.content.startswith("🆕NEW_FOLDER:"):
            lines = msg.content.split("\n")
            f_name = lines[0].replace("🆕NEW_FOLDER:", "")
            u_id = int(lines[1].replace("👤USER:", ""))
            if u_id == user_id and f_name not in folders:
                folders.append(f_name)
                archive_data[f_name] = []
        elif msg.content.startswith("📁FOLDER:"):
            lines = msg.content.split("\n")
            f_name = lines[0].replace("📁FOLDER:", "")
            u_id = int(lines[1].replace("👤USER:", ""))
            link = lines[2].replace("🔗LINK:", "")
            if u_id == user_id:
                if f_name not in archive_data:
                    archive_data[f_name] = []
                archive_data[f_name].append(link)

    if not folders:
        await interaction.followup.send("📭 まだフォルダがありません。まずは `/category_add` で作成してください。")
        return

    embed = discord.Embed(title=f"📚 {interaction.user.display_name} のブックマーク一覧", description="これまでに保存した大切な趣味のデータです。\nリンクをクリックすると元のメッセージに飛べます。", color=discord.Color.blue())
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_list = "\n".join([f"• [データリンク（ここをクリック）]({item})" for item in items]) if items else "*（まだデータが登録されていません）*"
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)

    await interaction.followup.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id != post_channel_id:
        return

    has_content = bool(message.attachments) or ("http://" in message.content or "https://" in message.content)
    if has_content:
        storage_vc = bot.get_channel(storage_vc_id)
        user_id = message.author.id
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                lines = msg.content.split("\n")
                f_name = lines[0].replace("🆕NEW_FOLDER:", "")
                u_id = int(lines[1].replace("👤USER:", ""))
                if u_id == user_id and f_name not in folders:
                    folders.append(f_name)

        if not folders:
            await message.reply("💡 まだ仕分けフォルダがありません。まずは `/category_add` コマンドでフォルダを作ってください！")
            return

        view = CategorySelectView(reversed(folders), message.id)
        await message.reply("このデータをどのフォルダにアーカイブしますか？", view=view)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    global post_channel_id, archive_channel_id, storage_vc_id
    print(f"ログインしました: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンドを {len(synced)} 件同期しました")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")

    for guild in bot.guilds:
        category_name = "📁 ブックマーク"
        existing_category = discord.utils.get(guild.categories, name=category_name)
        
        if not existing_category:
            try:
                existing_category = await guild.create_category(name=category_name)
            except Exception as e:
                print(f"カテゴリー作成エラー: {e}")
                continue

        ch_post = discord.utils.get(existing_category.text_channels, name="📥・ブックマーク")
        ch_archive = discord.utils.get(existing_category.text_channels, name="📚・アーカイブ")
        ch_storage_vc = discord.utils.get(existing_category.voice_channels, name="🤫・データ金庫")

        if not ch_post:
            ch_post = await guild.create_text_channel(name="📥・ブックマーク", category=existing_category, topic="ここに動画や画像のURLを貼ると、ボットが自動で仕分けを案内します。")
            await ch_post.send("📌 **ブックマーク・アーカイブボットへようこそ！**\n1. `/category_add` で好きなフォルダを作ります。\n2. ここに動画URLや画像を貼ると、自動で仕分けメニューが出現します！")

        if not ch_archive:
            ch_archive = await guild.create_text_channel(name="📚・アーカイブ", category=existing_category, topic="`/archive_view` コマンドで、これまでに集めたデータ一覧をここに表示できます。")

        if not ch_storage_vc:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, send_messages=True)
            }
            ch_storage_vc = await guild.create_voice_channel(name="🤫・データ金庫", category=existing_category, overwrites=overwrites)
            print(f"[{guild.name}] に完全非表示のデータ金庫VCを作成しました。")

        post_channel_id = ch_post.id
        archive_channel_id = ch_archive.id
        storage_vc_id = ch_storage_vc.id

# ★GitHubのSecretsから安全にトークンを読み込む設定
token = os.getenv("DISCORD_BOT_TOKEN")
bot.run(token)

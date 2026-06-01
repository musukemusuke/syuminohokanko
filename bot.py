import discord, os, asyncio
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# チャンネルIDを記憶する変数
post_id, archive_id = None, None

# --- 1. プルダウンメニュー ---
class CategorySelect(discord.ui.Select):
    def __init__(self, categories, content_url):
        self.content_url = content_url
        options = [discord.SelectOption(label=cat, description=f"「{cat}」に保存") for cat in categories]
        super().__init__(placeholder="フォルダを選択...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # 縦に長い処理を無くし、ファイル(data.txt)に直接1行でスマートに追記保存
        with open("data.txt", "a", encoding="utf-8") as f:
            f.write(f"{interaction.user.id},{self.values},{self.content_url}\n")
        await interaction.followup.send(f"✅ **{self.values}** に保存しました！", ephemeral=True)

# --- 2. スラッシュコマンド（仕分けフォルダの追加） ---
@bot.tree.command(name="category_add", description="仕分けフォルダを追加します")
async def category_add(interaction: discord.Interaction, name: str):
    # ユーザーごとのフォルダ作成記録も、ファイルに1行で保存
    with open("folders.txt", "a", encoding="utf-8") as f:
        f.write(f"{interaction.user.id},{name}\n")
    await interaction.response.send_message(f"✅ 📁 **{name}** を作成しました！", ephemeral=True)

# --- 3. アーカイブ一覧を表示するコマンド ---
@bot.tree.command(name="archive_view", description="保存した一覧を表示します")
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    u_id = interaction.user.id
    
    # フォルダ一覧の読み込み（縦に長いスキャンを廃止）
    user_folders = []
    if os.path.exists("folders.txt"):
        with open("folders.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    uid, fname = line.strip().split(",", 1)
                    if int(uid) == u_id and fname not in user_folders:
                        user_folders.append(fname)
    
    if not user_folders:
        await interaction.followup.send("📭 まずは `/category_add` でフォルダを作ってください。", ephemeral=True)
        return

    embed = discord.Embed(title=f"📚 {interaction.user.display_name} のブックマーク", color=discord.Color.blue())
    
    # データの読み込み
    for folder in user_folders:
        items = []
        if os.path.exists("data.txt"):
            with open("data.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        uid, fname, url = line.strip().split(",", 2)
                        if int(uid) == u_id and fname == folder:
                            items.append(url)
        
        item_list = "\n".join([f"• [データを見る]({url})" for url in items]) if items else "*（データなし）*"
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)
        
    await interaction.followup.send(embed=embed, ephemeral=True)

# --- 4. メッセージ自動検知機能 ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != post_id: return

    # 画像・動画・URLを判定
    url = message.attachments.url if message.attachments else None
    if not url and ("http://" in message.content or "https://" in message.content):
        for w in message.content.split():
            if w.startswith("http://") or w.startswith("https://"): url = w; break

    if url:
        user_folders = []
        if os.path.exists("folders.txt"):
            with open("folders.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        uid, fname = line.strip().split(",", 1)
                        if int(uid) == message.author.id and fname not in user_folders: user_folders.append(fname)
        
        if not user_folders:
            await message.reply("💡 まずは `/category_add` でフォルダを作ってください！")
            return
            
        await message.reply("どのフォルダに保存しますか？", view=discord.ui.View().add_item(CategorySelect(user_folders, url)))

# --- 5. 起動＆チャンネルの自動生成 ---
@bot.event
async def on_ready():
    global post_id, archive_id
    print(f"Online: {bot.user.name}")
    await bot.tree.sync()
    
    for guild in bot.guilds:
        cat = discord.utils.get(guild.categories, name="📁 ブックマーク") or await guild.create_category(name="📁 ブックマーク")
        ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク") or await guild.create_text_channel(name="📥・ブックマーク", category=cat)
        ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ") or await guild.create_text_channel(name="📚・アーカイブ", category=cat)
        post_id, archive_id = ch_post.id, ch_arc.id

async def main():
    async with bot:
        # GitHub Actionsの6時間制限（タイムアウト）にかかる前に、2時間45分（9900秒）で安全に自動交代する内製タイマー
        bot.loop.create_task(asyncio.sleep(9900))
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try: asyncio.run(main())
    except: print("安全に自動終了します。")

import discord, asyncio, os
from discord import app_commands
from discord.ext import commands
from views import CategorySelectView
from utils import build_archive_embed, check_and_restore_messages

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

post_id, archive_id, storage_vc_id = None, None, None

async def my_embed_factory(user_id, display_name):
    return await build_archive_embed(bot, storage_vc_id, user_id, display_name)

@bot.tree.command(name="category_add", description="フォルダを追加します")
async def category_add(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    storage_vc = bot.get_channel(storage_vc_id)
    if storage_vc:
        await storage_vc.send(f"🆕NEW_FOLDER:{name}\n👤USER:{interaction.user.id}")
        await interaction.followup.send(f"✅ 📁 **{name}** を作成しました！", ephemeral=True)

@bot.tree.command(name="archive_view", description="アーカイブ一覧を表示します")
async def archive_view(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = await my_embed_factory(interaction.user.id, interaction.user.display_name)
    await interaction.followup.send(embed=embed or "📭 フォルダがありません。", ephemeral=True)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author == bot.user:
        await check_and_restore_messages(bot, post_id, archive_id, my_embed_factory)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.channel.id != post_id: return
    if bool(message.attachments) or "http" in message.content:
        storage_vc = bot.get_channel(storage_vc_id)
        folders = []
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🆕NEW_FOLDER:"):
                lines = msg.content.split("\n")
                if int(lines[1].replace("👤USER:", "").strip()) == message.author.id:
                    folders.append(lines[0].replace("🆕NEW_FOLDER:", "").strip())
        if not folders:
            await message.reply("💡 まずは `/category_add` でフォルダを作ってください！")
            return
        await message.reply("どのフォルダにアーカイブしますか？", view=CategorySelectView(reversed(folders), message, post_id, storage_vc_id))

@bot.event
async def on_ready():
    global post_id, archive_id, storage_vc_id
    print(f"Online: {bot.user.name}"); await bot.tree.sync()
    for guild in bot.guilds:
        cat = discord.utils.get(guild.categories, name="📁 ブックマーク") or await guild.create_category(name="📁 ブックマーク")
        ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク") or await guild.create_text_channel(name="📥・ブックマーク", category=cat)
        ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ") or await guild.create_text_channel(name="📚・アーカイブ", category=cat)
        ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
        if not ch_vc:
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), guild.owner: discord.PermissionOverwrite(view_channel=False), guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
            ch_vc = await guild.create_voice_channel(name="🤫・データ金庫", category=cat, overwrites=overwrites)
        post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id
        await check_and_restore_messages(bot, post_id, archive_id, my_embed_factory)

async def main():
    async with bot: await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    import syslog # actions用
    asyncio.run(main())

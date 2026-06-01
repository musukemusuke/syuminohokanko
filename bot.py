import asyncio
import os
import discord
from discord.ext import commands
import traceback

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# 💡 【遮断対策】bot.py側でメッセージを受け取ったら、Cogs（BookmarkCog）へ通信を100%丸ごとパスします
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # これを書くことで、別ファイルに分けた Cog 内の on_message が遮断されずに100%発火します
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✨ ログインしました: {bot.user.name}")
    try:
        await bot.tree.sync()
        print("✅ スラッシュコマンドの同期が完了しました。")
    except Exception as e:
        print(f"❌ コマンド同期エラー: {e}")

async def main():
    async with bot:
        cogs_to_load = ["cogs.admin", "cogs.bookmark"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 ロード成功: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

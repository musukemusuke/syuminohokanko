import asyncio
import os
import discord
from discord.ext import commands
import traceback

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"✨ ログインしました: {bot.user.name}")
    try:
        # スラッシュコマンドをDiscord側と完全同期
        await bot.tree.sync()
        print("✅ スラッシュコマンドの同期が完了しました。")
    except Exception as e:
        print(f"❌ コマンド同期エラー: {e}")

async def main():
    async with bot:
        # 💡 cogs フォルダ内のプログラムを自動で読み込む
        cogs_to_load = ["cogs.admin", "cogs.bookmark"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 クラスをロードしました: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        # ボットの起動
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

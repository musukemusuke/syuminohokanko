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

async def main():
    async with bot:
        # Cogsファイルをボットにロード
        cogs_to_load = ["cogs.admin", "cogs.commands", "cogs.listener"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 ロード成功: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        # 💡 【完全解決】連続呼び出しを廃止し、引数なしの sync() 1回だけで
        # 内部の最新コマンド（nameとurl必須）へDiscord側を一括で書き換え同期させます。
        try:
            print("🔄 最新のスラッシュコマンド（name/url必須仕様）をDiscordと完全同期中...")
            await bot.tree.sync()
            print("✅ すべてのスラッシュコマンドの同期が完了しました！")
        except Exception as e:
            print(f"❌ コマンド同期エラー: {e}")

        # ボットの起動
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

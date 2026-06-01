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
        # 正しいファイルを順番にロード
        cogs_to_load = ["cogs.admin", "cogs.commands", "cogs.listener"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 ロード成功: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        # 💡 【完全上書き同期】すべてのファイルを読み込み終わった「後」に、
        # 確実に Discord サーバーへ最新のコマンド定義（name/url必須仕様）を一括で強制登録します。
        try:
            print("🔄 スラッシュコマンド（name/url必須仕様）をDiscordへ完全同期中...")
            await bot.tree.sync()
            print("✅ すべてのスラッシュコマンドの画面更新が完了しました！")
        except Exception as e:
            print(f"❌ コマンド同期エラー: {e}")

        # ボットの起動
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

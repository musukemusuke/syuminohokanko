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
        # 💡 正しいCogsファイルのみを厳密にロードします
        cogs_to_load = ["cogs.admin", "cogs.commands", "cogs.listener"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 ロード成功: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        # 💡 【完全治療】グローバル同期を廃止し、参加している各サーバーへ即時同期を実行します
        try:
            print("🔄 スラッシュコマンド（name/url必須仕様）を各サーバーへ即時同期中...")
            
            # 起動時に所属しているサーバーすべてに対して強制的に即時同期をかけます
            for guild in bot.guilds:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"  → サーバー「{guild.name}」への即時同期が完了しました")
                
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

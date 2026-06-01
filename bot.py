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

        # 💡 【重要修正：キャッシュの強制上書き】
        # 一度、Discord側にある古いスラッシュコマンドの定義を完全に空（クリア）にします。
        try:
            print("🗑️ 古いスラッシュコマンドのキャッシュをクリア中...")
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
            
            # その直後に、新しく読み込んだ必須項目（nameとurl）つきの最新コマンドを上書き再同期します。
            print("🔄 新しいスラッシュコマンド（必須urlつき）を完全強制同期中...")
            await bot.tree.sync()
            print("✅ すべてのスラッシュコマンドの強制上書き同期が完了しました！")
        except Exception as e:
            print(f"❌ コマンドの強制同期エラー: {e}")

        # ボットの起動
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

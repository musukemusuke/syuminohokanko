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
        # 💡 正しい3つのファイルだけを厳密に読み込みます
        cogs_to_load = ["cogs.admin", "cogs.commands", "cogs.listener"]
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"📦 ロード成功: {cog}")
            except Exception as e:
                print(f"❌ クラス {cog} のロードに失敗しました:")
                traceback.print_exc()

        # 💡 【重要：過去のコマンドの完全な上書き】
        # bot.tree.sync() を実行する前に、現在のボットの「新しいコマンドリスト」で
        # Discordサーバー側にある古い履歴（bookmark.pyの残骸）を完全に上書きして置き換えます。
        try:
            print("🗑️ Discord側の古いコマンド履歴を完全に上書き消去中...")
            
            # 登録されている全サーバーの古いグローバルコマンドを最新の3つのファイルで強制上書き
            await bot.tree.sync(guild=None)
            
            print("✅ すべてのスラッシュコマンドの履歴が完全に入れ替わりました！")
        except Exception as e:
            print(f"❌ コマンド同期エラー: {e}")

        # ボットの起動
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        traceback.print_exc()

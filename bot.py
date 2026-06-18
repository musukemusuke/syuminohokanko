import asyncio
import os
import discord
from discord.ext import commands
import traceback

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print(f"✅ ログイン成功: {bot.user} ({bot.user.id})")
    print(f"📊 参加サーバー: {len(bot.guilds)} サーバー")

    # アクティビティ（ステータス）を設定
    await bot.change_presence(activity=discord.Game(name="作:@musuke.exe (musuke)"))
    
    # コマンドの増殖・重複を完全に防止するクリーンな同期を実行
    if len(bot.guilds) <= 5:
        await sync_all_commands()


async def load_cogs():
    cogs = ["cogs.admin", "cogs.commands", "cogs.listener"]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cog ロード成功: {cog}")
        except Exception as e:
            print(f"❌ Cog ロード失敗: {cog}")
            traceback.print_exc()


async def sync_all_commands():
    """コマンド同期専用関数（増殖防止版）"""
    print("🔄 コマンド同期開始...")
    try:
        # copy_global_toによる重複バグを完全に防ぐため、グローバル同期のみを実行
        await bot.tree.sync() 
        print("✅ グローバルコマンドの同期が完了しました")
        return True
    except Exception as e:
        print(f"❌ 同期エラー: {e}")
        traceback.print_exc()
        return False


async def main():
    async with bot:
        # 拡張機能（Cog）をロード
        await load_cogs()

        # トークンチェックを最初に行う
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("❌ DISCORD_BOT_TOKEN が設定されていません")
            return
            
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 停止します...")
    except Exception as e:
        traceback.print_exc()

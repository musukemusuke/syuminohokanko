import asyncio
import os
import discord
from discord.ext import commands
import traceback

# ====================== Bot設定 ======================
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


async def load_cogs():
    cogs = ["cogs.admin", "cogs.commands", "cogs.listener"]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cog ロード成功: {cog}")
        except Exception as e:
            print(f"❌ Cog ロード失敗: {cog}")
            traceback.print_exc()


async def sync_all_commands(guild: discord.Guild = None):
    """同期専用関数"""
    print("🔄 コマンド同期を開始...")

    try:
        if guild:  # 特定サーバーのみ
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"→ {guild.name} に同期完了")
        else:  # 全サーバー
            for g in bot.guilds:
                bot.tree.copy_global_to(guild=g)
                await bot.tree.sync(guild=g)
                print(f"→ {g.name} に同期完了")
                await asyncio.sleep(0.8)  # レート制限対策
        print("✅ コマンド同期完了")
        return True
    except Exception as e:
        print(f"❌ 同期エラー: {e}")
        traceback.print_exc()
        return False


async def main():
    async with bot:
        await load_cogs()

        # 起動時は最小限の同期（参加サーバーが少ない場合のみ）
        if bot.guilds and len(bot.guilds) <= 5:   # 5サーバー以下なら自動同期
            await sync_all_commands()

        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("❌ DISCORD_BOT_TOKEN が設定されていません")
            return

        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 ボットを停止します...")
    except Exception as e:
        traceback.print_exc()

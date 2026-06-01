import asyncio
import os
import discord
from discord.ext import commands
import traceback

# ====================== 基本設定 ======================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",  # スラッシュコマンドメインなのでプレフィックスはほぼ使わない
    intents=intents,
    help_command=None   # デフォルトhelpを無効化（任意）
)


@bot.event
async def on_ready():
    print(f"✨ ログイン成功: {bot.user} ({bot.user.id})")
    print(f"📊 参加サーバー数: {len(bot.guilds)} サーバー")


async def load_cogs():
    """cogを安全にロード"""
    cogs = [
        "cogs.admin",
        "cogs.commands", 
        "cogs.listener"
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cogロード成功: {cog}")
        except Exception as e:
            print(f"❌ Cogロード失敗: {cog}")
            traceback.print_exc()


async def sync_commands():
    """スラッシュコマンドの同期（起動時は最小限に）"""
    print("🔄 スラッシュコマンド同期を開始...")
    
    synced_count = 0
    for guild in bot.guilds:
        try:
            # 必要に応じて一度クリア（コマンドが消えない問題対策）
            # bot.tree.clear_commands(guild=guild)
            
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            
            print(f"   → {guild.name} ({guild.id}) に同期完了")
            synced_count += 1
            
            await asyncio.sleep(0.7)  # レート制限対策（少し余裕を持たせる）
            
        except discord.HTTPException as e:
            print(f"   ⚠️  {guild.name} 同期エラー: {e.status} {e.text}")
        except Exception as e:
            print(f"   ❌  {guild.name} で予期せぬエラー: {e}")

    print(f"✅ 同期完了: {synced_count}/{len(bot.guilds)} サーバー")


async def main():
    async with bot:
        await load_cogs()
        
        # 同期は起動時でも行うが、控えめに
        if bot.guilds:
            await sync_commands()
        else:
            print("⚠️ 現在どのサーバーにも参加していません。")

        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("❌ DISCORD_BOT_TOKEN が環境変数に設定されていません。")
            return
            
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ボットを停止します...")
    except Exception as e:
        traceback.print_exc()

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
    
    # 【修正箇所1】ログイン完了後（サーバー情報が読み込まれた後）に同期を実行する
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


async def sync_all_commands(guild=None):
    """コマンド同期専用関数"""
    print("🔄 コマンド同期開始...")
    try:
        if guild:  # 特定サーバー
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"→ {guild.name} に同期完了")
        else:  # 全サーバー
            # 【修正箇所2】グローバルコマンドの同期に変更（または各サーバーへの適切な同期）
            # 5サーバー以下なら一応ループでも動きますが、通常は以下の一行だけで十分です
            await bot.tree.sync() 
            print("→ グローバル同期が完了しました（反映に最大1時間かかる場合があります）")
            
        print("✅ コマンド同期完了")
        return True
    except Exception as e:
        print(f"❌ 同期エラー: {e}")
        traceback.print_exc()
        return False


async def main():
    async with bot:
        # 1. 拡張機能（Cog）をロードする
        await load_cogs()

        # 【修正箇所3】ボットのトークンチェックをログイン前に確実に行う
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("❌ DISCORD_BOT_TOKEN が設定されていません")
            return
            
        # 2. Discordに接続（ログイン）する
        # ※ボットが起動した後に「on_ready」の中で自動的にコマンド同期が走ります
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 停止します...")
    except Exception as e:
        traceback.print_exc()

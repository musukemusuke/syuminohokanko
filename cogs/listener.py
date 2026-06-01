import asyncio
import re
import discord
from discord.ext import commands

# 💡 views.py から新設したトリガービューをインポート
from views import EphemeralTriggerView

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return

        import cogs.commands as cmd
        
        if message.guild and (not cmd.post_id or not cmd.storage_vc_id):
            cmd.load_channel_ids(message.guild)

        if message.channel.id != cmd.post_id: return

        # URLの抽出判定
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match: return

        url_list = [url_match.group(0)]
        user_id = message.author.id

        # メモリから爆速でフォルダ一覧を取得（ここで絶対にタイムアウトしません）
        folders = cmd.cached_folders.get(user_id, [])

        if not folders:
            await cmd.sync_all_cached_folders(self.bot)
            folders = cmd.cached_folders.get(user_id, [])
            if not folders:
                await message.reply("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください！")
                return

        # 元のURL投稿を即座に削除（チャットを一切汚さない）
        try: await message.delete()
        except: pass

        # 💡 【遮断・タイムアウト対策】
        # Discordの制限に引っかからない安全な「中継用ボタンメッセージ」をチャンネルへ一瞬で送信します
        trigger_view = EphemeralTriggerView(reversed(folders), url_list, cmd.post_id, cmd.storage_vc_id)
        
        embed_reply = discord.Embed(
            description=f"🔷 **{message.author.mention} がURLを投稿しました**\n下のボタンを押してフォルダに仕分けしてください。",
            color=0x2f3136
        )
        await message.channel.send(embed=embed_reply, view=trigger_view)

        # 画面の自動更新
        async def refresh_task():
            await asyncio.sleep(2)
            cmd_cog = self.bot.get_cog("CommandsCog")
            if cmd_cog:
                await cmd_cog.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
            
        self.bot.loop.create_task(refresh_task())

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

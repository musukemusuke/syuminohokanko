import asyncio
import re
import discord
from discord.ext import commands

from cogs.commands import get_guild_data
from views import CategorySelectView

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        commands_cog = self.bot.get_cog("CommandsCog")
        if not commands_cog:
            return

        data = get_guild_data(message.guild.id)

        if not data["post_id"]:
            commands_cog.load_channel_ids(message.guild)

        if message.channel.id != data["post_id"]:
            return

        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match:
            return

        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return

        # ユーザー専用プライベートスレッドの読み込み
        target_thread = await commands_cog.get_or_create_user_thread(storage_channel, message.author)

        # スレッドの履歴からバックグラウンドでフォルダを最新に同期
        folders = await commands_cog.sync_user_folders_from_history(target_thread, message.author.id)
        data["folders"][message.author.id] = folders

        if not folders:
            await message.reply("❌ まだフォルダがありません。先に `/category_add` でフォルダを作成してください。", delete_after=10)
            return

        try:
            await message.delete()
        except discord.Forbidden:
            print("⚠️ メッセージの管理権限がありません。")
        except discord.NotFound:
            pass

        # スレッドオブジェクト（target_thread）を第4引数へ安全に引き渡し
        view = CategorySelectView(
            categories=list(reversed(folders)), 
            original_urls=[url_match.group(0)], 
            post_id=data["post_id"], 
            target_dest=target_thread
        )
        
        embed = discord.Embed(
            title="📥 保存先フォルダを選択してください", 
            description=f"**投稿者:** {message.author.mention}\n**URL:**\n{url_match.group(0)}", 
            color=0x2f3136
        )
        
        sent_message = await message.channel.send(embed=embed, view=view, delete_after=90)
        view.message = sent_message

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

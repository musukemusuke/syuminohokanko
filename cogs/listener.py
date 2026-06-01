import asyncio
import re
import discord
from discord.ext import commands

from views import CategorySelectView

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # CommandsCogからデータ取得
        commands_cog = self.bot.get_cog("CommandsCog")
        if not commands_cog:
            return

        data = get_guild_data(message.guild.id)  # commands.pyの関数をそのまま使用したい場合はimport

        if not data["post_id"]:
            commands_cog.load_channel_ids(message.guild)

        if message.channel.id != data["post_id"]:
            return

        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match:
            return

        folders = data["folders"].get(message.author.id, [])

        if not folders:
            await message.reply("`/category_add` でフォルダを作成してください。", delete_after=10)
            return

        try:
            await message.delete()
        except:
            pass

        view = CategorySelectView(reversed(folders), [url_match.group(0)], data["post_id"], data["storage_vc_id"])
        embed = discord.Embed(title="📥 保存先を選択", description=f"URL:\n{url_match.group(0)}", color=0x2f3136)
        await message.channel.send(embed=embed, view=view, delete_after=90)  # ephemeralが使えないので制限時間付き

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

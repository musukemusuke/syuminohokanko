import discord
from discord.ext import commands

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🚨 ご指示の通り、チャンネルにURLを貼ったときの自動保存メニュー起動処理を完全に消去しました。
    # これにより、テキストチャンネルにリンクを送信してもボットは一切干渉せず何も反応しなくなります。

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

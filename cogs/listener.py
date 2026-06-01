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
        if message.author.bot: return

        import cogs.commands as cmd
        
        if message.guild and (not cmd.post_id or not cmd.storage_vc_id):
            cmd.load_channel_ids(message.guild)

        if message.channel.id != cmd.post_id: return

        # URLの抽出
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match: return

        url_list = [url_match.group(0)]
        user_id = message.author.id

        folders = cmd.cached_folders.get(user_id, [])

        if not folders:
            await cmd.sync_all_cached_folders(self.bot)
            folders = cmd.cached_folders.get(user_id, [])
            if not folders:
                await message.reply("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください！")
                return

        try: await message.delete()
        except: pass

        try:
            webhook = await message.channel.create_webhook(name="Archiver-Proxy")
            view = CategorySelectView(reversed(folders), url_list, cmd.post_id, cmd.storage_vc_id)
            embed = discord.Embed(
                title="📥 URLの保管先を選択",
                description=f"対象のURL:\n{url_list}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
                color=0x2f3136
            )
            await webhook.send(
                embed=embed, 
                view=view, 
                ephemeral=True, 
                username=self.bot.user.name, 
                avatar_url=self.bot.user.display_avatar.url
            )
            await webhook.delete()
        except Exception as e:
            print(f"[ERROR] エフェメラル配信エラー: {e}")

        async def refresh_task():
            await asyncio.sleep(2)
            cmd_cog = self.bot.get_cog("CommandsCog")
            if cmd_cog:
                await cmd_cog.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
            
        self.bot.loop.create_task(refresh_task())

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

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

        # 💡 commands.py 側から共有IDとフォルダキャッシュを安全にインポート
        import cogs.commands as cmd_module
        if message.guild and (not cmd_module.post_id or not cmd_module.storage_vc_id):
            cmd_module.load_channel_ids(message.guild)

        if message.channel.id != cmd_module.post_id: return

        # URLの抽出判定
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match: return

        url_list = [url_match.group(0)]
        memo_text = message.content.strip()
        user_id = message.author.id

        # 💡 メモリキャッシュから一瞬で引き出すため、絶対にタイムアウトしません
        folders = cmd_module.cached_folders.get(user_id, [])

        if not folders:
            await cmd_module.sync_all_cached_folders(self.bot)
            folders = cmd_module.cached_folders.get(user_id, [])
            if not folders:
                await message.reply("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください！")
                return

        # 元のURL投稿を即座に削除（チャットを一切汚さない）
        try: await message.delete()
        except: pass

        # Webhookを生成して、最初から完全エフェメラル（自分限定）でメニューを送信
        try:
            webhook = await message.channel.create_webhook(name="Archiver-Proxy")
            view = CategorySelectView(reversed(folders), url_list, cmd_module.post_id, cmd_module.storage_vc_id)
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

        # 画面の自動更新をバックグラウンド実行（commands.py内の関数を再利用）
        async def refresh_task():
            await asyncio.sleep(2)
            cmd_cog = self.bot.get_cog("CommandsCog")
            if cmd_cog:
                await cmd_cog.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
            
        self.bot.loop.create_task(refresh_task())

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

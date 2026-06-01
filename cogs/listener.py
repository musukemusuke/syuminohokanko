import asyncio
import re
import discord
from discord.ext import commands

from views import CategorySelectView

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._commands_cog = None  # 後で取得

    def get_commands_cog(self):
        if self._commands_cog is None:
            self._commands_cog = self.bot.get_cog("CommandsCog")
        return self._commands_cog

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        commands_cog = self.get_commands_cog()
        if not commands_cog:
            return

        # チャンネルID取得（commands_cog側で管理している想定）
        if not commands_cog.post_id or not commands_cog.storage_vc_id:
            commands_cog.load_channel_ids(message.guild)

        if message.channel.id != commands_cog.post_id:
            return

        # URL抽出
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match:
            return

        url_list = [url_match.group(0)]
        user_id = message.author.id

        # キャッシュからフォルダ取得
        folders = commands_cog.cached_folders.get(user_id, [])

        # キャッシュにない場合は金庫から復元（初回 or 再起動後用）
        if not folders:
            folders = await self._recover_folders_from_vault(commands_cog, user_id)
            if folders:
                commands_cog.cached_folders[user_id] = folders

        if not folders:
            try:
                await message.reply("💡 まだフォルダがありません。`/category_add` で作成してください！", delete_after=15)
            except:
                pass
            return

        # 元メッセージを即削除
        try:
            await message.delete()
        except:
            pass

        # エフェメラル風メッセージ送信（Webhookは最小限に）
        try:
            await self._send_ephemeral_selection(message, folders, url_list, commands_cog)
        except Exception as e:
            print(f"[Listener] エラー: {e}")

        # アーカイブ画面更新
        if message.guild:
            asyncio.create_task(self._refresh_archive(commands_cog, message.guild, user_id, message.author.display_name))

    async def _recover_folders_from_vault(self, commands_cog, user_id: int):
        """金庫からユーザーのフォルダを復元"""
        storage_vc = self.bot.get_channel(commands_cog.storage_vc_id)
        if not storage_vc:
            return []

        folders = []
        try:
            async for msg in storage_vc.history(limit=800):  # 必要に応じて調整
                if not msg.content.startswith("🆕NEW_FOLDER:"):
                    continue
                lines = msg.content.split("\n")
                f_name = None
                u_id = None
                for line in lines:
                    if line.startswith("🆕NEW_FOLDER:"):
                        f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id = int(line.replace("👤USER:", "").strip())
                if f_name and u_id == user_id and f_name not in folders:
                    folders.append(f_name)
        except Exception as e:
            print(f"[Vault Recovery] Error: {e}")

        return folders

    async def _send_ephemeral_selection(self, message, folders, url_list, commands_cog):
        """Webhookを使わない代替案も検討可能ですが、ひとまず改善版"""
        webhook = await message.channel.create_webhook(name="Archiver")
        try:
            view = CategorySelectView(
                reversed(folders), 
                url_list, 
                commands_cog.post_id, 
                commands_cog.storage_vc_id
            )
            embed = discord.Embed(
                title="📥 URLの保管先を選択",
                description=f"対象のURL:\n{url_list[0]}",
                color=0x2f3136
            )
            await webhook.send(
                embed=embed,
                view=view,
                ephemeral=True,
                username=self.bot.user.display_name,
                avatar_url=self.bot.user.display_avatar.url
            )
        finally:
            await asyncio.sleep(3)  # 少し待ってから削除
            await webhook.delete()

    async def _refresh_archive(self, commands_cog, guild, user_id, display_name):
        await asyncio.sleep(1.5)
        try:
            await commands_cog.update_archive_channel_embed(guild, user_id, display_name)
        except:
            pass


async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

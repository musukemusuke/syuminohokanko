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

        # URLの抽出判定
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match: return

        url_list = [url_match.group(0)]
        user_id = message.author.id

        # 記憶されたメモリ（キャッシュ）から引き出す
        folders = cmd.cached_folders.get(user_id, [])

        if not folders:
            await cmd.sync_all_cached_folders(self.bot)
            folders = cmd.cached_folders.get(user_id, [])
            if not folders:
                await message.reply("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください！")
                return

        # 💡 【新機能】データ金庫から、各フォルダに紐づいているURL履歴を1つずつ抽出する処理
        folder_url_map = {f: [] for f in folders}
        try:
            storage_vc = self.bot.get_channel(cmd.storage_vc_id)
            async for msg in storage_vc.history(limit=500):
                content = msg.content
                if content.startswith("📁FOLDER:"):
                    lines = content.split("\n")
                    f_name, u_id, link = None, None, None
                    for line in lines:
                        if line.startswith("📁FOLDER:"): 
                            f_name = cmd.clean_folder_name(line.replace("📁FOLDER:", ""))
                        elif line.startswith("👤USER:"): 
                            u_id = line.replace("👤USER:", "").strip()
                        elif line.startswith("🔗LINK:"): 
                            link = line.replace("🔗LINK:", "").strip()
                    
                    if f_name and u_id and link and int(u_id) == user_id:
                        if f_name in folder_url_map and link not in folder_url_map[f_name]:
                            folder_url_map[f_name].append(link)
        except:
            pass

        # 元のURL投稿を即座に削除
        try: await message.delete()
        except: pass

        # 💡 抽出した「フォルダ名とURL履歴のデータ（folder_url_map）」を丸ごとセレクトメニューに渡す
        try:
            webhook = await message.channel.create_webhook(name="Archiver-Proxy")
            view = CategorySelectView(reversed(folders), url_list, cmd.post_id, cmd.storage_vc_id, folder_url_map)
            embed = discord.Embed(
                title="📥 URLの保管先を選択",
                description=f"対象のURL:\n{url_list[0]}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
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

        # 画面の自動更新
        async def refresh_task():
            await asyncio.sleep(2)
            cmd_cog = self.bot.get_cog("CommandsCog")
            if cmd_cog:
                await cmd_cog.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
            
        self.bot.loop.create_task(refresh_task())

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

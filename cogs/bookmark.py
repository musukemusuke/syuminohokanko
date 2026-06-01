import asyncio
import re
import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs
from views import CategorySelectView

# チャンネル管理用のグローバルID
post_id, archive_id, storage_vc_id = None, None, None

def load_channel_ids(guild: discord.Guild):
    global post_id, archive_id, storage_vc_id
    cat = discord.utils.get(guild.categories, name="📁 ブックマーク")
    if not cat:
        return False
    
    ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク")
    ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ")
    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
    
    if ch_post and ch_arc and ch_vc:
        post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id
        return True
    return False

class BookmarkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def my_embed_factory(self, user_id, display_name):
        if not storage_vc_id:
            return None
        return await build_archive_embed(
            self.bot, storage_vc_id, user_id, display_name
        )

    async def update_archive_channel_embed(self, guild, user_id, display_name):
        if not archive_id:
            return
        ch_archive = self.bot.get_channel(archive_id)
        if not ch_archive:
            return
        new_embed = await self.my_embed_factory(user_id, display_name)
        if not new_embed:
            return

        async for msg in ch_archive.history(limit=20):
            if msg.author == self.bot.user and msg.embeds:
                await msg.edit(embed=new_embed)
                print(f"[{guild.name}] アーカイブ画面を自動更新しました。")
                break

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if load_channel_ids(guild):
                print(f"[{guild.name}] のチャンネル設定を自動復元しました。")

    @app_commands.command(
        name="category_add",
        description="新しくデータを仕分けるフォルダ（カテゴリー）を追加します",
    )
    @app_commands.describe(name="追加するフォルダ名（例：動画、イラスト、ゲームなど）")
    async def category_add(self, interaction: discord.Interaction, name: str):
        global storage_vc_id
        if not storage_vc_id and interaction.guild:
            load_channel_ids(interaction.guild)

        storage_vc = self.bot.get_channel(storage_vc_id)
        if not storage_vc:
            await interaction.response.send_message("❌ まだ `/setup` が完了していないか、金庫が見つかりません。", ephemeral=True)
            return
            
        await storage_vc.send(
            f"🆕NEW_FOLDER:{name}\n" f"👤USER:{interaction.user.id}"
        )
        
        embed = discord.Embed(
            description=f"📂 フォルダ 「**{name}**」 を新規作成しました！\n「📥・ブックマーク」から仕分け可能になります。",
            color=0xd4af37
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="category_delete",
        description="作成したフォルダ（カテゴリー）を中身のデータごと完全に削除します",
    )
    @app_commands.describe(name="削除したいフォルダ名")
    async def category_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild:
            load_channel_ids(interaction.guild)

        if not storage_vc_id:
            await interaction.followup.send("❌ セットアップが完了していません。", ephemeral=True)
            return

        success = await delete_category_logs(self.bot, storage_vc_id, interaction.user.id, name)
        
        if success:
            embed = discord.Embed(
                description=f"🗑️ フォルダ 「**{name}**」 とその中のアーカイブデータをすべて削除しました。",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            if interaction.guild:
                self.bot.loop.create_task(self.update_archive_channel_embed(interaction.guild, interaction.user.id, interaction.user.display_name))
        else:
            await interaction.followup.send(f"❌ フォルダ 「{name}」 が見つからなかったか、あなたが作成したフォルダではありません。", ephemeral=True)

    @app_commands.command(
        name="archive_view", 
        description="自分が保存したアーカイブ一覧を表示します"
    )
    async def archive_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild:
            load_channel_ids(interaction.guild)

        embed = await self.my_embed_factory(
            interaction.user.id, interaction.user.display_name
        )
        if embed is None:
            await interaction.followup.send(
                "📭 まだフォルダがありません。まずは `/category_add` で作成してください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="archive_search",
        description="キーワードを使って、自分がこれまでに保存したデータを検索します",
    )
    @app_commands.describe(keyword="検索したい言葉（フォルダ名、リンクなど）")
    async def archive_search(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild:
            load_channel_ids(interaction.guild)

        if not storage_vc_id:
            await interaction.followup.send("❌ セットアップが完了していません。", ephemeral=True)
            return

        embed = await search_archive_data(
            self.bot, storage_vc_id, interaction.user.id, keyword
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # 💡 【完全修正】bot.pyから中継された通信を受け取る、正しいCog型イベントリスナー
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        global post_id, storage_vc_id
        if message.author.bot:
            return

        if message.guild and (not post_id or not storage_vc_id):
            load_channel_ids(message.guild)

        if message.channel.id != post_id:
            return

        storage_vc = self.bot.get_channel(storage_vc_id)
        if not storage_vc:
            return

        # URL判定
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match:
            return

        url_list = [url_match.group(0)]
        memo_text = message.content.strip()

        user_id = message.author.id
        folders = []
        deleted_folders = []

        try:
            async for msg in storage_vc.history(limit=1000):
                content = msg.content
                lines = content.split("\n")
                
                if content.startswith("🆕NEW_FOLDER:"):
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"):
                            f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                            
                    if f_name and u_id_text and int(u_id_text) == user_id:
                        if f_name not in folders and f_name not in deleted_folders:
                            folders.append(f_name)

                elif content.startswith("🗑️DELETE_FOLDER:"):
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🗑️DELETE_FOLDER:"):
                            f_name = line.replace("🗑️DELETE_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                            
                    if f_name and u_id_text and int(u_id_text) == user_id:
                        deleted_folders.append(f_name)
        except Exception as e:
            print(f"[ERROR] フォルダ取得エラー: {e}")

        folders = [f for f in folders if f not in deleted_folders]

        if not folders:
            await message.reply(
                "💡 まだ仕分けフォルダがありません。まずは `/category_add` コマンドでフォルダを作ってください！"
            )
            return

        view = CategorySelectView(
            reversed(folders), url_list, post_id, storage_vc_id, memo_text
        )
        
        embed_reply = discord.Embed(
            description="🔷 **このコンテンツの保管先フォルダを選択してください**",
            color=0x2f3136
        )
        await message.reply(embed=embed_reply, view=view)

        async def refresh_task():
            await asyncio.sleep(2)
            await self.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
            
        self.bot.loop.create_task(refresh_task())

async def setup(bot):
    await bot.add_cog(BookmarkCog(bot))

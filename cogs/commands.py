import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs
from views import CategorySelectView

# グローバル変数・キャッシュ
post_id, archive_id, storage_vc_id = None, None, None
cached_folders = {} # {user_id: [folder_names]}

def load_channel_ids(guild: discord.Guild):
    global post_id, archive_id, storage_vc_id
    cat = discord.utils.get(guild.categories, name="📁 ブックマーク")
    if not cat: return False
    
    ch_post = discord.utils.get(cat.text_channels, name="📥・ブックマーク")
    ch_arc = discord.utils.get(cat.text_channels, name="📚・アーカイブ")
    ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")
    
    if ch_post and ch_arc and ch_vc:
        post_id, archive_id, storage_vc_id = ch_post.id, ch_arc.id, ch_vc.id
        return True
    return False

def clean_folder_name(name: str) -> str:
    if not name: return ""
    cleaned = name.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"): cleaned = cleaned[1:-1].strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (cleaned.startswith('"') and cleaned.endswith('"')): cleaned = cleaned[1:-1].strip()
    return cleaned

async def sync_all_cached_folders(bot_instance):
    global storage_vc_id
    storage_vc = bot_instance.get_channel(storage_vc_id)
    if not storage_vc: return

    print("🔄 バックグラウンドでフォルダデータの事前集計を開始...")
    temp_folders, temp_deleted = {}, {}

    try:
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
            if content.startswith("🆕NEW_FOLDER:"):
                f_name, u_id = None, None
                for line in lines:
                    if line.startswith("🆕NEW_FOLDER:"): f_name = clean_folder_name(line.replace("🆕NEW_FOLDER:", ""))
                    elif line.startswith("👤USER:"): u_id = int(line.replace("👤USER:", "").strip())
                if f_name and u_id:
                    if u_id not in temp_folders: temp_folders[u_id] = []
                    if f_name not in temp_folders[u_id]: temp_folders[u_id].append(f_name)

            elif content.startswith("🗑️DELETE_FOLDER:"):
                f_name, u_id = None, None
                for line in lines:
                    if line.startswith("🗑️DELETE_FOLDER:"): f_name = clean_folder_name(line.replace("🗑️DELETE_FOLDER:", ""))
                    elif line.startswith("👤USER:"): u_id = int(line.replace("👤USER:", "").strip())
                if f_name and u_id:
                    if u_id not in temp_deleted: temp_deleted[u_id] = []
                    if f_name not in temp_deleted[u_id]: temp_deleted[u_id].append(f_name)
        
        for u_id in temp_folders:
            deleted = temp_deleted.get(u_id, [])
            cached_folders[u_id] = [f for f in temp_folders[u_id] if f not in deleted]
        print("✅ フォルダデータの事前集計が完了しました。")
    except Exception as e:
        print(f"❌ 事前集計エラー: {e}")

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def my_embed_factory(self, user_id, display_name):
        if not storage_vc_id: return None
        return await build_archive_embed(self.bot, storage_vc_id, user_id, display_name)

    async def update_archive_channel_embed(self, guild, user_id, display_name):
        if not archive_id: return
        ch_archive = self.bot.get_channel(archive_id)
        if not ch_archive: return
        new_embed = await self.my_embed_factory(user_id, display_name)
        if not new_embed: return

        async for msg in ch_archive.history(limit=20):
            if msg.author == self.bot.user and msg.embeds:
                await msg.edit(embed=new_embed)
                print(f"[{guild.name}] アーカイブ画面を自動更新しました。")
                break

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            load_channel_ids(guild)
        await sync_all_cached_folders(self.bot)

    # 💡 【完全自分専用仕様】URLを最初から誰にも見られずにフォルダへ格納する新しいコマンド
    @app_commands.command(name="archive_add", description="【自分専用表示】URLを指定したフォルダへ安全に格納します")
    @app_commands.describe(url="保存したいウェブサイトや動画のURL")
    async def archive_add(self, interaction: discord.Interaction, url: str):
        global post_id, storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        
        user_id = interaction.user.id
        folders = cached_folders.get(user_id, [])

        if not folders:
            await sync_all_cached_folders(self.bot)
            folders = cached_folders.get(user_id, [])
            if not folders:
                await interaction.response.send_message("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください。", ephemeral=True)
                return

        # 💡 スラッシュコマンド起点なので、最初から100%確実に自分だけにしか見えないセレクトメニューが出せます！
        view = CategorySelectView(reversed(folders), [url], post_id, storage_vc_id)
        embed = discord.Embed(
            title="📥 URLの保管先を選択",
            description=f"対象のURL:\n{url}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
            color=0x2f3136
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        if interaction.guild:
            self.bot.loop.create_task(self.update_archive_channel_embed(interaction.guild, interaction.user.id, interaction.user.display_name))

    @app_commands.command(name="category_add", description="新しくデータを仕分けるフォルダカテゴリーを追加します")
    async def category_add(self, interaction: discord.Interaction, name: str):
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        storage_vc = self.bot.get_channel(storage_vc_id)
        if not storage_vc:
            await interaction.response.send_message("❌ まだ `/setup` が完了していないか、金庫が見つかりません。", ephemeral=True)
            return
            
        await storage_vc.send(f"🆕NEW_FOLDER:{name}\n👤USER:{interaction.user.id}")
        await sync_all_cached_folders(self.bot)
        
        embed = discord.Embed(description=f"📂 フォルダ 「**{name}**」 を新規作成しました！", color=0xd4af37)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="category_delete", description="作成したフォルダカテゴリーを中身ごと完全に削除します")
    async def category_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        if not storage_vc_id:
            await interaction.followup.send("❌ セットアップが完了していません。", ephemeral=True)
            return

        if await delete_category_logs(self.bot, storage_vc_id, interaction.user.id, name):
            await sync_all_cached_folders(self.bot)
            embed = discord.Embed(description=f"🗑️ フォルダ 「**{name}**」 とそのデータをすべて削除しました。", color=0xe74c3c)
            await interaction.followup.send(embed=embed, ephemeral=True)
            if interaction.guild:
                self.bot.loop.create_task(self.update_archive_channel_embed(interaction.guild, interaction.user.id, interaction.user.display_name))
        else:
            await interaction.followup.send(f"❌ フォルダ 「{name}」 が見つからないか、権限がありません。", ephemeral=True)

    @app_commands.command(name="archive_view", description="自分が保存したアーカイブ一覧を表示します")
    async def archive_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        
        embed = await self.my_embed_factory(interaction.user.id, interaction.user.display_name)
        if embed is None:
            await interaction.followup.send("📭 まだフォルダがありません。", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="archive_search", description="キーワードを使って保存したデータを検索します")
    async def archive_search(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        if not storage_vc_id:
            await interaction.followup.send("❌ セットアップが完了していません。", ephemeral=True)
            return

        embed = await search_archive_data(self.bot, storage_vc_id, interaction.user.id, keyword)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))

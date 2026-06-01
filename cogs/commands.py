import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs

# 共有用のグローバル変数
post_id, archive_id, storage_vc_id = None, None, None
# 💡 【タイムアウト撲滅】激重な1000件ループを完全に廃止し、メモリ上で爆速管理します
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

    # 💡 起動時に最新のコマンド設定（/category_addの変更など）をDiscordへ強制反映させます
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            load_channel_ids(guild)
            try:
                # サーバーごとに最新のコマンドツリーを同期（即時反映）
                self.bot.tree.copy_global_to(guild=guild)
                await self.bot.tree.sync(guild=guild)
                print(f"[{guild.name}] へ最新のコマンドを同期しました！")
            except Exception as e:
                print(f"[{guild.name}] 同期エラー: {e}")
        print("✅ 趣味の保管庫システムがオンラインになりました。")

    @app_commands.command(name="archive_add", description="【自分専用表示】URLを指定したフォルダへ安全に格納します")
    @app_commands.describe(url="保存したいウェブサイトや動画のURL")
    async def archive_add(self, interaction: discord.Interaction, url: str):
        global post_id, storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        
        user_id = interaction.user.id
        folders = cached_folders.get(user_id, [])

        if not folders:
            await interaction.response.send_message("💡 まだ仕分けフォルダがありません。まずは `/category_add` で作成してください。", ephemeral=True)
            return

        from views import CategorySelectView
        view = CategorySelectView(reversed(folders), [url], post_id, storage_vc_id)
        embed = discord.Embed(
            title="📥 URLの保管先を選択",
            description=f"対象のURL:\n{url}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
            color=0x2f3136
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        if interaction.guild:
            self.bot.loop.create_task(self.update_archive_channel_embed(interaction.guild, interaction.user.id, interaction.user.display_name))

    # 💡 【完全必須化 ＆ 3秒ルール完全回避】
    @app_commands.command(name="category_add", description="新しくデータを仕分けるフォルダカテゴリーを追加します")
    @app_commands.describe(name="追加するフォルダ名（例：動画、イラストなど）", url="このフォルダの基本となるURLリンク（例：https://youtube.com）")
    async def category_add(self, interaction: discord.Interaction, name: str, url: str):
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        storage_vc = self.bot.get_channel(storage_vc_id)
        if not storage_vc:
            await interaction.response.send_message("❌ まだ `/setup` が完了していないか、金庫が見つかりません。", ephemeral=True)
            return
            
        # 💡 通信を待たせないために、最初にDiscordへ「了解！」の返信を ephemeral で一瞬で返します（3秒タイムアウトを100%回避）
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        # 💡 メモリ上のフォルダリストに即座に名前を追加（通信を挟まないため0.001秒で終わります）
        if user_id not in cached_folders:
            cached_folders[user_id] = []
        if name not in cached_folders[user_id]:
            cached_folders[user_id].append(name)
            
        # 裏でゆっくりデータ金庫（VC）にログを書き込みます
        await storage_vc.send(
            f"🆕NEW_FOLDER:{name}\n"
            f"👤USER:{user_id}\n"
            f"🔗LINK:{url}"
        )
        
        embed = discord.Embed(
            description=f"📂 フォルダ 「**{name}**」 を新規作成しました！\n🔗 フォルダのベースURL: {url}",
            color=0xd4af37
        )
        # defer していたレスポンスを確定させます
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="category_delete", description="作成したフォルダカテゴリーを中身ごと完全に削除します")
    @app_commands.describe(name="削除したいフォルダ名")
    async def category_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        global storage_vc_id
        if not storage_vc_id and interaction.guild: load_channel_ids(interaction.guild)
        if not storage_vc_id:
            await interaction.followup.send("❌ セットアップが完了していないか、金庫が見つかりません。", ephemeral=True)
            return

        user_id = interaction.user.id
        # メモリ上から即座に削除
        if user_id in cached_folders and name in cached_folders[user_id]:
            cached_folders[user_id].remove(name)

        if await delete_category_logs(self.bot, storage_vc_id, user_id, name):
            embed = discord.Embed(description=f"🗑️ フォルダ 「**{name}**」 とそのデータをすべて削除しました。", color=0xe74c3c)
            await interaction.followup.send(embed=embed, ephemeral=True)
            if interaction.guild:
                self.bot.loop.create_task(self.update_archive_channel_embed(interaction.guild, user_id, interaction.user.display_name))
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
    @app_commands.describe(keyword="検索したい言葉")
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

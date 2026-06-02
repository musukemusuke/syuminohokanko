import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs, _parse_log
from views import CategorySelectView

# ====================== 状態管理 ======================
guild_data = {}

def get_guild_data(guild_id: int):
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "post_id": None,
            "archive_id": None,
            "storage_channel_id": None,
            "folders": {}  # user_id -> [folder_names]
        }
    return guild_data[guild_id]


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_channel_ids(self, guild: discord.Guild):
        if not guild:
            return False
        data = get_guild_data(guild.id)

        cat = discord.utils.get(guild.categories, name="📁 ブックマーク")
        if not cat:
            return False

        data["post_id"] = discord.utils.get(cat.text_channels, name="📥・ブックマーク").id if discord.utils.get(cat.text_channels, name="📥・ブックマーク") else None
        data["archive_id"] = discord.utils.get(cat.text_channels, name="📚・アーカイブ").id if discord.utils.get(cat.text_channels, name="📚・アーカイブ") else None
        
        storage_ch = discord.utils.get(cat.text_channels, name="🤫・データ金庫")
        data["storage_channel_id"] = storage_ch.id if storage_ch else None

        return bool(data["storage_channel_id"])

    async def get_or_create_user_thread(self, channel: discord.TextChannel, user: discord.User) -> discord.Thread:
        """ユーザー専用のプライベートスレッドを取得または新規作成する"""
        thread_name = f"🔒-{user.id}-{user.name}"
        
        # 既存のアクティブなスレッドを探索
        for thread in channel.threads:
            if thread.name == thread_name:
                return thread
                
        # アーカイブされたスレッドも含めて探索
        try:
            async for thread in channel.archived_threads(private=True, limit=100):
                if thread.name == thread_name:
                    await thread.edit(archived=False) # 再利用のために展開
                    return thread
        except Exception:
            pass

        # 見つからない場合は新しくプライベートスレッドを作成
        new_thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        return new_thread

    async def sync_user_folders_from_history(self, thread: discord.Thread, user_id: int) -> list:
        """スレッド内の過去履歴からユーザーのフォルダ一覧を自動復元する"""
        detected_folders = set()
        try:
            async for msg in thread.history(limit=1000):
                content = msg.content.strip()
                if "NEW_FOLDER" in content:
                    parsed = _parse_log(content)
                    f_name = parsed.get("NEW_FOLDER")
                    u_id = parsed.get("USER")
                    if f_name and u_id and int(u_id) == user_id:
                        detected_folders.add(f_name)
        except Exception:
            pass
        return sorted(list(detected_folders))

    # ====================== コマンド ======================

    @app_commands.command(name="category_add", description="新しくフォルダを作成します")
    @app_commands.describe(name="フォルダ名", url="フォルダの代表となるURL")
    async def category_add(self, interaction: discord.Interaction, name: str, url: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内のみ使用可能です", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if not data["storage_channel_id"]:
            self.load_channel_ids(interaction.guild)

        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return await interaction.followup.send("❌ データ金庫が見つかりません。\n`/setup` を実行してください。", ephemeral=True)

        # ユーザー専用プライベートスレッドの取得/作成
        target_thread = await self.get_or_create_user_thread(storage_channel, interaction.user)
        user_id = interaction.user.id
        
        # スレッド履歴から同期
        data["folders"][user_id] = await self.sync_user_folders_from_history(target_thread, user_id)

        if name not in data["folders"][user_id]:
            data["folders"][user_id].append(name)
            data["folders"][user_id].sort()

        # スレッドに向けてデータを送信
        await target_thread.send(f"NEW_FOLDER:{name}\nUSER:{user_id}\nLINK:{url}")

        await interaction.followup.send(f"✅ フォルダ「**{name}**」を作成しました！", ephemeral=True)

    @app_commands.command(name="category_delete", description="フォルダと中身をすべて削除します")
    @app_commands.describe(name="削除するフォルダ名")
    async def category_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if not data["storage_channel_id"]:
            self.load_channel_ids(interaction.guild)

        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return await interaction.followup.send("❌ データ金庫が見つかりません。", ephemeral=True)

        target_thread = await self.get_or_create_user_thread(storage_channel, interaction.user)

        # チャンネルではなくスレッドオブジェクトをそのまま渡してログを削除
        if await delete_category_logs(self.bot, target_thread, interaction.user.id, name):
            data["folders"][interaction.user.id] = await self.sync_user_folders_from_history(target_thread, interaction.user.id)
            await interaction.followup.send(f"🗑️ フォルダ「**{name}**」とその中身を完全に削除しました。", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ 指定されたフォルダ「{name}」のログデータが見つかりませんでした。", ephemeral=True)

    @app_commands.command(name="archive_view", description="自分のアーカイブ一覧を表示します")
    async def archive_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if not data["storage_channel_id"]:
            self.load_channel_ids(interaction.guild)

        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return await interaction.followup.send("❌ データ金庫が見つかりません。", ephemeral=True)

        target_thread = await self.get_or_create_user_thread(storage_channel, interaction.user)

        embed = await build_archive_embed(
            self.bot, target_thread, interaction.user.id, interaction.user.display_name
        )

        if not embed:
            await interaction.followup.send("まだフォルダがありません。`/category_add` で作成してください。", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="archive_search", description="保存したデータから検索します")
    @app_commands.describe(keyword="検索キーワード")
    async def archive_search(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if not data["storage_channel_id"]:
            self.load_channel_ids(interaction.guild)

        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return await interaction.followup.send("❌ データ金庫が見つかりません。", ephemeral=True)

        target_thread = await self.get_or_create_user_thread(storage_channel, interaction.user)

        embed = await search_archive_data(
            self.bot, target_thread, interaction.user.id, keyword
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))

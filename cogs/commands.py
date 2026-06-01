import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs
from views import CategorySelectView

# ====================== 状態管理 ======================
guild_data = {}  # {guild_id: {post_id, archive_id, storage_vc_id, folders}}

def get_guild_data(guild_id: int):
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "post_id": None,
            "archive_id": None,
            "storage_vc_id": None,
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
        data["storage_vc_id"] = discord.utils.get(cat.voice_channels, name="🤫・データ金庫").id if discord.utils.get(cat.voice_channels, name="🤫・データ金庫") else None

        return bool(data["storage_vc_id"])

    # ====================== コマンド ======================

    @app_commands.command(name="category_add", description="新しくフォルダを作成します")
    @app_commands.describe(name="フォルダ名", url="フォルダの代表となるURL")
    async def category_add(self, interaction: discord.Interaction, name: str, url: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内のみ使用可能です", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if not data["storage_vc_id"]:
            self.load_channel_ids(interaction.guild)

        storage_vc = self.bot.get_channel(data["storage_vc_id"])
        if not storage_vc:
            return await interaction.followup.send("❌ データ金庫が見つかりません。\n`/setup` を実行してください。", ephemeral=True)

        user_id = interaction.user.id
        if user_id not in data["folders"]:
            data["folders"][user_id] = []

        if name not in data["folders"][user_id]:
            data["folders"][user_id].append(name)
            data["folders"][user_id].sort()

        await storage_vc.send(f"🆕NEW_FOLDER:{name}\n👤USER:{user_id}\n🔗LINK:{url}")

        await interaction.followup.send(f"✅ フォルダ「**{name}**」を作成しました！", ephemeral=True)

    @app_commands.command(name="archive_add", description="URLをフォルダに保存します")
    @app_commands.describe(url="保存したいURL")
    async def archive_add(self, interaction: discord.Interaction, url: str):
        if not interaction.guild: 
            return await interaction.response.send_message("サーバー内のみ使用可能です", ephemeral=True)

        data = get_guild_data(interaction.guild.id)
        folders = data["folders"].get(interaction.user.id, [])

        if not folders:
            return await interaction.response.send_message("`/category_add` でフォルダを作成してください。", ephemeral=True)

        view = CategorySelectView(reversed(folders), [url], data["post_id"], data["storage_vc_id"])
        embed = discord.Embed(
            title="📥 保存先を選択してください",
            description=f"URL:\n{url}",
            color=0x2f3136
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="category_delete", description="フォルダと中身をすべて削除します")
    @app_commands.describe(name="削除するフォルダ名")
    async def category_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        if await delete_category_logs(self.bot, data["storage_vc_id"], interaction.user.id, name):
            folders = data["folders"].get(interaction.user.id, [])
            if name in folders:
                folders.remove(name)
            await interaction.followup.send(f"🗑️ 「**{name}**」を完全に削除しました。", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ 「{name}」が見つかりません。", ephemeral=True)

    @app_commands.command(name="archive_view", description="自分のアーカイブ一覧を表示します")
    async def archive_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)

        embed = await build_archive_embed(
            self.bot, data["storage_vc_id"], interaction.user.id, interaction.user.display_name
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

        embed = await search_archive_data(
            self.bot, data["storage_vc_id"], interaction.user.id, keyword
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))

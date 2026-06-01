import discord
from discord import app_commands
from discord.ext import commands

from utils import build_archive_embed, search_archive_data, delete_category_logs
from views import CategorySelectView

# guild_id ごとにデータを管理
guild_data = {}  # {guild_id: {"post_id":, "archive_id":, "storage_vc_id":, "folders": {user_id: [names]}}}

def get_guild_data(guild_id: int):
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "post_id": None,
            "archive_id": None,
            "storage_vc_id": None,
            "folders": {}
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
    @app_commands.describe(name="フォルダ名", url="フォルダの代表URL")
    async def category_add(self, interaction: discord.Interaction, name: str, url: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内のみ使用可能です", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        data = get_guild_data(interaction.guild.id)
        storage_vc = self.bot.get_channel(data["storage_vc_id"])

        if not storage_vc:
            self.load_channel_ids(interaction.guild)
            storage_vc = self.bot.get_channel(data["storage_vc_id"])
            if not storage_vc:
                return await interaction.followup.send("❌ データ金庫が見つかりません。`/setup`を実行してください。", ephemeral=True)

        user_id = interaction.user.id
        if user_id not in data["folders"]:
            data["folders"][user_id] = []
        if name not in data["folders"][user_id]:
            data["folders"][user_id].append(name)
            data["folders"][user_id].sort()

        await storage_vc.send(f"🆕NEW_FOLDER:{name}\n👤USER:{user_id}\n🔗LINK:{url}")

        await interaction.followup.send(
            f"✅ フォルダ「**{name}**」を作成しました！", ephemeral=True
        )

    @app_commands.command(name="archive_add", description="URLをフォルダに保存します")
    @app_commands.describe(url="保存したいURL")
    async def archive_add(self, interaction: discord.Interaction, url: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内のみ使用可能です", ephemeral=True)

        data = get_guild_data(interaction.guild.id)
        folders = data["folders"].get(interaction.user.id, [])

        if not folders:
            return await interaction.response.send_message("`/category_add` で先にフォルダを作成してください。", ephemeral=True)

        view = CategorySelectView(reversed(folders), [url], data["post_id"], data["storage_vc_id"])
        embed = discord.Embed(title="📥 保存先を選択", description=f"URL:\n{url}", color=0x2f3136)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # 他のコマンド（archive_view, archive_search, category_delete）も同様に実装可能です
    # 必要なら追加で出します

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))

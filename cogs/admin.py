import discord
from discord import app_commands
from discord.ext import commands
import traceback

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="【管理者専用】ブックマークシステムの初期設定を行います")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channels(self, interaction: discord.Interaction):
        # ...（前回の改善版をそのまま使用。変更なしでも可）
        # 省略（必要なら言ってください）
        await interaction.response.defer(ephemeral=True)
        # 既存のsetup処理...
        commands_cog = self.bot.get_cog("CommandsCog")
        if commands_cog and hasattr(commands_cog, "load_channel_ids"):
            commands_cog.load_channel_ids(interaction.guild)


    @app_commands.command(name="sync", description="【管理者専用】スラッシュコマンドを強制同期します")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        success = await self.bot.get_cog("AdminCog").bot.get_command("sync_all_commands")  # 待機中
        # 実際は main.py の関数を呼ぶより、直接同期処理をここに書くのがシンプル

        try:
            await interaction.followup.send("🔄 同期中...", ephemeral=True)
            bot = interaction.client
            bot.tree.copy_global_to(guild=interaction.guild)
            await bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("✅ このサーバーのコマンドを強制同期しました。", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 同期失敗: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

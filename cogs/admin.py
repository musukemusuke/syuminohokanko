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
        await interaction.response.defer(ephemeral=True)
        
        # 既存のsetup処理（チャンネル作成など）をここに記述
        
        # チャンネルIDを他Cogに通知（※永続化の実装を推奨）
        commands_cog = self.bot.get_cog("CommandsCog")
        if commands_cog and hasattr(commands_cog, "load_channel_ids"):
            commands_cog.load_channel_ids(interaction.guild)
            
        await interaction.followup.send("✅ 初期設定が完了しました。", ephemeral=True)


    @app_commands.command(name="sync", description="【管理者専用】スラッシュコマンドを強制同期します")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        # 1. 応答を保留にする（これによって「ボットが考え中...」の状態になる）
        await interaction.response.defer(ephemeral=True)

        try:
            # 2. 保留していた応答の最初のメッセージ（親メッセージ）を送信する
            msg = await interaction.followup.send("🔄 コマンド同期を実行中...（数秒かかります）", ephemeral=True)
            
            bot = interaction.client
            # グローバルに登録されているスラッシュコマンドを、現在のサーバーに複製して即時反映させる
            bot.tree.copy_global_to(guild=interaction.guild)
            await bot.tree.sync(guild=interaction.guild)
            
            # 3. 送信したメッセージの内容を「完了」に書き換える（edit_messageを使用）
            await interaction.followup.edit_message(
                message_id=msg.id, 
                content="✅ このサーバーに対するスラッシュコマンドの強制同期が完了しました！"
            )
            
        except Exception as e:
            traceback.print_exc()
            # エラー時もメッセージを書き換えてユーザーに通知する
            await interaction.followup.send(f"❌ 同期中にエラーが発生しました: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

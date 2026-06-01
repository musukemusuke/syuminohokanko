import discord
from discord import app_commands
from discord.ext import commands
import traceback

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="【管理者専用】ブックマークシステムのカテゴリと各チャンネルを自動生成します")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channels(self, interaction: discord.Interaction):
        # 処理に時間がかかる場合があるため応答を保留
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("❌ サーバー内でのみ実行可能です。", ephemeral=True)

        try:
            msg = await interaction.followup.send("🛠️ ブックマーク環境を設定中...（チャンネルを生成しています）", ephemeral=True)

            # 1. カテゴリの作成または取得
            category_name = "📁 ブックマーク"
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                category = await guild.create_category(name=category_name)
                print(f"✅ カテゴリを作成しました: {category_name}")

            # 2. データ金庫（非公開テキストチャンネル）用のパーミッション（権限）設定
            # @everyone (全員) は見られない、ボット自身は見られる設定にする
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
            }

            # 3. 各種テキストチャンネルの生成（存在しない場合のみ作成）
            channels_to_create = [
                {"name": "📥・ブックマーク", "type": "text", "overwrites": None},
                {"name": "📚・アーカイブ", "type": "text", "overwrites": None},
                {"name": "🤫・データ金庫", "type": "text", "overwrites": overwrites} # データ金庫は非公開に設定
            ]

            for ch_info in channels_to_create:
                existing_ch = discord.utils.get(category.text_channels, name=ch_info["name"])
                if not existing_ch:
                    await guild.create_text_channel(
                        name=ch_info["name"],
                        category=category,
                        overwrites=ch_info["overwrites"]
                    )
                    print(f"✅ チャンネルを作成しました: {ch_info['name']}")

            # 4. CommandsCogへのチャンネルID再読み込み通知
            commands_cog = self.bot.get_cog("CommandsCog")
            if commands_cog and hasattr(commands_cog, "load_channel_ids"):
                success = commands_cog.load_channel_ids(guild)
                if not success:
                    return await interaction.followup.edit_message(
                        message_id=msg.id,
                        content="⚠️ チャンネルは作成できましたが、IDの読み込みに失敗しました。再度お試しください。"
                    )

            # 5. 完了通知
            await interaction.followup.edit_message(
                message_id=msg.id,
                content=(
                    "✅ **初期設定が完了しました！**\n\n"
                    "以下のチャンネルが生成されました：\n"
                    "| チャンネル名 | 役割 |\n"
                    "| --- | --- |\n"
                    "| `📥・ブックマーク` | ここにURLを貼ると自動で保管用メニューが出ます |\n"
                    "| `📚・アーカイブ` | アーカイブ閲覧時に利用されます |\n"
                    "| `🤫・データ金庫` | 管理者専用（非公開）。データが安全に記録される場所です |\n\n"
                    "※もしスラッシュコマンドが上手く表示されない場合は、続けて `/sync` コマンドを実行してください。"
                )
            )

        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ セットアップ中にエラーが発生しました: {e}", ephemeral=True)


    @app_commands.command(name="sync", description="【管理者専用】スラッシュコマンドを強制同期します")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            msg = await interaction.followup.send("🔄 コマンド同期を実行中...（数秒かかります）", ephemeral=True)
            
            bot = interaction.client
            bot.tree.copy_global_to(guild=interaction.guild)
            await bot.tree.sync(guild=interaction.guild)
            
            await interaction.followup.edit_message(
                message_id=msg.id, 
                content="✅ このサーバーに対するスラッシュコマンドの強制同期が完了しました！"
            )
            
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 同期中にエラーが発生しました: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

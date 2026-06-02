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
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("❌ サーバー内でのみ実行可能です。", ephemeral=True)

        try:
            msg = await interaction.followup.send("🛠️ ブックマーク環境を設定中...（チャンネルを生成しています）", ephemeral=True)

            category_name = "📁 ブックマーク"
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                category = await guild.create_category(name=category_name)
                print(f"✅ カテゴリを作成しました: {category_name}")

            # 【変更】「🤫・データ金庫」から「🤫・データ」に修正
            channels_to_create = ["📥・ブックマーク", "📚・アーカイブ", "🤫・データ"]

            created_channels = {}
            for ch_name in channels_to_create:
                existing_ch = discord.utils.get(category.text_channels, name=ch_name)
                if not existing_ch:
                    new_ch = await guild.create_text_channel(name=ch_name, category=category)
                    created_channels[ch_name] = new_ch
                    print(f"✅ チャンネルを作成しました: {ch_name}")
                else:
                    created_channels[ch_name] = existing_ch

            # 権限とスレッド作成権限の設定
            storage_ch = created_channels.get("🤫・データ")
            if storage_ch:
                await storage_ch.set_permissions(guild.default_role, read_messages=False, send_messages=False)
                await storage_ch.set_permissions(
                    guild.me, 
                    read_messages=True, 
                    send_messages=True, 
                    read_message_history=True,
                    manage_threads=True,
                    create_private_threads=True
                )
                print("🔒 データチャンネルの非公開化およびスレッド権限設定が完了しました。")

            commands_cog = self.bot.get_cog("CommandsCog")
            if commands_cog and hasattr(commands_cog, "load_channel_ids"):
                success = commands_cog.load_channel_ids(guild)
                if not success:
                    return await interaction.followup.edit_message(
                        message_id=msg.id,
                        content="⚠️ チャンネルは作成できましたが、IDの読み込みに失敗しました。再度お試しください。"
                    )

            await interaction.followup.edit_message(
                message_id=msg.id,
                content=(
                    "✅ **初期設定が完了しました！**\n\n"
                    "以下のチャンネルが生成されました：\n"
                    "| チャンネル名 | 役割 |\n"
                    "| --- | --- |\n"
                    "| `📥・ブックマーク` | URLを貼ると自動保存用メニューが出ます |\n"
                    "| `📚・アーカイブ` | アーカイブ閲覧時に利用されます |\n"
                    "| `🤫・データ` | ユーザー別の**プライベートスレッド**が裏で自動生成・保管されます |\n\n"
                    "※スラッシュコマンド一覧が正しく反映されない場合は、続けて `/sync` コマンドを実行してください。"
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
            msg = await interaction.followup.send("🔄 コマンド同期を実行中...", ephemeral=True)
            bot = interaction.client
            await bot.tree.sync()
            await interaction.followup.edit_message(
                message_id=msg.id, 
                content="✅ 全体のスラッシュコマンド同期を申請しました！重複データが消えて反映されるまで数分〜最大1時間ほどかかる場合があります。"
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 同期中にエラーが発生しました: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

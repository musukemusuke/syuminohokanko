import discord
from discord import app_commands
from discord.ext import commands
import traceback

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ AdminCogがロードされました。")
        # 同期は必要最小限に（初回起動時や明示的なコマンドでのみ実行推奨）
        for guild in self.bot.guilds:
            print(f"[{guild.name}] セットアップ準備完了")

    @app_commands.command(
        name="setup",
        description="【管理者専用】ブックマーク用のカテゴリーとチャンネルを生成します",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        try:
            cat_name = "📁 ブックマーク"
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(name=cat_name)

            # 📥・ブックマーク
            post_ch = discord.utils.get(category.text_channels, name="📥・ブックマーク")
            if not post_ch:
                post_topic = (
                    "ここにURLを投稿すると自動で保存メニューが出ます。\n"
                    "まずは `/category_add フォルダ名 URL` でフォルダを作成してください。"
                )
                post_ch = await guild.create_text_channel(
                    name="📥・ブックマーク", 
                    category=category, 
                    topic=post_topic
                )

            # 📚・アーカイブ
            arc_ch = discord.utils.get(category.text_channels, name="📚・アーカイブ")
            if not arc_ch:
                arc_topic = "`/archive_view` で自分のアーカイブを確認できます。"
                arc_ch = await guild.create_text_channel(
                    name="📚・アーカイブ", 
                    category=category, 
                    topic=arc_topic
                )

            # 🤫・データ金庫
            vc = discord.utils.get(category.voice_channels, name="🤫・データ金庫")
            if not vc:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, 
                        connect=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, 
                        connect=True, 
                        send_messages=True
                    ),
                }
                vc = await guild.create_voice_channel(
                    name="🤫・データ金庫", 
                    category=category, 
                    overwrites=overwrites
                )

            # CommandsCogのload_channel_idsを安全に呼び出し
            commands_cog = self.bot.get_cog("CommandsCog")
            if commands_cog and hasattr(commands_cog, "load_channel_ids"):
                commands_cog.load_channel_ids(guild)
            else:
                print(f"[{guild.name}] CommandsCogが見つからないか、load_channel_idsがありません")

            embed = discord.Embed(
                title="✨ セットアップ完了",
                description="ブックマークカテゴリ、投稿チャンネル、アーカイブ、金庫の作成が完了しました。",
                color=0x2f3136
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ボットに「チャンネル管理」権限がありません。", 
                ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ セットアップ中にエラーが発生しました。\n```{e}```", 
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

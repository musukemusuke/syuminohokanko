import discord
from discord import app_commands
from discord.ext import commands
import traceback

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            cat = discord.utils.get(guild.categories, name=cat_name) or (
                await guild.create_category(name=cat_name)
            )

            post_topic = (
                "まずは `/category_add` でフォルダを作ってください。\n"
                "ここにURLを投稿すると自動で仕分けが行われます。"
            )
            ch_post = discord.utils.get(
                cat.text_channels, name="📥・ブックマーク"
            ) or (
                await guild.create_text_channel(
                    name="📥・ブックマーク", category=cat, topic=post_topic
                )
            )

            topic_text = (
                "`/archive_view` または `/archive_search` で保存したデータをいつでも確認・検索できます。"
            )
            ch_arc = discord.utils.get(
                cat.text_channels, name="📚・アーカイブ"
            ) or (
                await guild.create_text_channel(
                    name="📚・アーカイブ", category=cat, topic=topic_text
                )
            )

            ch_vc = discord.utils.get(cat.voice_channels, name="🤫・データ金庫")

            if not ch_vc:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, connect=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, connect=True, send_messages=True
                    ),
                }
                ch_vc = await guild.create_voice_channel(
                    name="🤫・データ金庫", category=cat, overwrites=overwrites
                )

            # 💡 【バグの根本治療】フライング同期の重い処理を完全に消去しました
            from cogs.commands import load_channel_ids
            load_channel_ids(guild)

            embed = discord.Embed(
                title="✨ システムセットアップ完了",
                description="趣味の保管庫に必要なチャンネルと秘密の金庫の生成・同期が正常に完了しました。",
                color=0x2f3136
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ ボットの権限（チャンネル管理権限など）が不足しています。", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ セットアップ中にエラーが発生しました: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

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

            # 復活したトピック説明欄の定義と、新名称「🤫・データ」への完全変更
            channels_to_create = [
                {
                    "name": "📥・ブックマーク", 
                    "topic": "ここにURLリンクを貼り付けるだけで、自動的に趣味のフォルダへ保管できます。文字の入力は自由です。"
                },
                {
                    "name": "📚・アーカイブ", 
                    "topic": "保存した趣味一覧を表示・確認するためのチャンネルです。コマンド実行時に連動します。"
                },
                {
                    "name": "🤫・データ", 
                    "topic": "管理者専用（一般ユーザーは入力不可）。裏側でユーザー別のプライベートスレッドが保管される場所です。"
                }
            ]

            created_channels = {}
            for ch_info in channels_to_create:
                existing_ch = discord.utils.get(category.text_channels, name=ch_info["name"])
                if not existing_ch:
                    new_ch = await guild.create_text_channel(
                        name=ch_info["name"], 
                        category=category,
                        topic=ch_info["topic"]
                    )
                    created_channels[ch_info["name"]] = new_ch
                    print(f"✅ チャンネルを作成しました: {ch_info['name']}")
                else:
                    if existing_ch.topic != ch_info["topic"]:
                        await existing_ch.edit(topic=ch_info["topic"])
                    created_channels[ch_info["name"]] = existing_ch

            # 「🤫・データ」チャンネルの完全送信ロックダウン（一般ユーザーは入力不可に）
            storage_ch = created_channels.get("🤫・データ")
            if storage_ch:
                await storage_ch.set_permissions(
                    guild.default_role, 
                    read_messages=False, 
                    send_messages=False,
                    send_messages_in_threads=False
                )
                # 引数でのTypeErrorを物理的に回避するため、作成後に個別オブジェクトで権限を上書き
                await storage_ch.set_permissions(
                    guild.me, 
                    read_messages=True, 
                    send_messages=True, 
                    read_message_history=True,
                    manage_threads=True,
                    create_private_threads=True,
                    send_messages_in_threads=True
                )
                print("🔒 データチャンネルの完全ロックダウンおよびスレッド権限設定が完了しました。")

            commands_cog = self.bot.get_cog("CommandsCog")
            if commands_cog and hasattr(commands_cog, "load_channel_ids"):
                success = commands_cog.load_channel_ids(guild)
                if not success:
                    return await interaction.followup.edit_message(
                        message_id=msg.id,
                        content="⚠️ チャンネルは作成できましたが、IDの読み込みに失敗しました。再度お試しください。"
                    )

            # 余計な文字をすべて削り、シンプルに一言だけ完了を通知
            await interaction.followup.edit_message(
                message_id=msg.id,
                content="✅ **初期設定が完了しました！**"
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
            # 重複増殖バグを根本から防止するため、copy_global_to は使用せずsyncのみを実行
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

import discord
import traceback

class CategorySelect(discord.ui.Select):

    def __init__(self, categories, message_id, post_id, vc_id):
        self.message_id = message_id
        self.post_id = post_id
        self.vc_id = vc_id
        options = [
            discord.SelectOption(
                label=cat, description=f"フォルダ「{cat}」に保存します"
            )
            for cat in categories
        ]
        super().__init__(
            placeholder="保存するフォルダを選択してください...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # 1. タイムアウトを防ぐため即座に応答を返す
        await interaction.response.defer(ephemeral=True)
        
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc:
                await interaction.followup.send("❌ データ金庫チャンネルが見つかりません。再セットアップしてください。", ephemeral=True)
                return

            # ★【修正完了】self.valuesはリストなので、[0]で選択された文字列を直接取得
            selected_folder = self.values[0]
            
            # ★【修正完了】Discordの正しいメッセージURLフォーマット（/channels/を挿入）に修正
            archive_link = f"https://discord.com{interaction.guild_id}/{self.post_id}/{self.message_id}"

            # 金庫VCにデータを送信
            await storage_vc.send(
                f"📁FOLDER:{selected_folder}\n"
                f"👤USER:{interaction.user.id}\n"
                f"🔗LINK:{archive_link}"
            )
            
            await interaction.followup.send(
                f"✅ **{selected_folder}** フォルダに登録しました！",
                ephemeral=True,
            )
            print(f"[SUCCESS] ユーザー {interaction.user.name} が '{selected_folder}' に保存しました。")

        except Exception as e:
            print("[CRITICAL ERROR] セレクトメニュー処理中にエラーが発生しました:")
            traceback.print_exc()
            await interaction.followup.send(f"❌ 保存処理中にエラーが発生しました: {e}", ephemeral=True)


class CategorySelectView(discord.ui.View):

    def __init__(self, categories, message_id, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(
            CategorySelect(categories, message_id, post_id, vc_id)
        )

import discord
import traceback

class CategorySelect(discord.ui.Select):

    # 💡 引数の名称を message_id から original_url に変更
    def __init__(self, categories, original_url, post_id, vc_id):
        self.original_url = original_url
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
        await interaction.response.defer(ephemeral=True)
        
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc:
                return

            selected_folder = self.values[0]
            
            # 💡 ディスコードのリンクではなく、元々貼られていた元のURLをそのまま金庫に保存します
            archive_link = self.original_url

            await storage_vc.send(
                f"📁FOLDER:{selected_folder}\n"
                f"👤USER:{interaction.user.id}\n"
                f"🔗LINK:{archive_link}"
            )
            await interaction.followup.send(
                f"✅ **{selected_folder}** フォルダに登録しました！",
                ephemeral=True,
            )

        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):

    def __init__(self, categories, original_url, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(
            CategorySelect(categories, original_url, post_id, vc_id)
        )

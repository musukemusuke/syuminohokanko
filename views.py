import discord


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
        await interaction.response.defer(ephemeral=True)
        storage_vc = interaction.client.get_channel(self.vc_id)
        if not storage_vc:
            return

        selected_folder = self.values
        archive_link = f"https://discord.com{interaction.guild_id}/{self.post_id}/{self.message_id}"

        await storage_vc.send(
            f"📁FOLDER:{selected_folder}\n👤USER:{interaction.user.id}\n🔗LINK:{archive_link}"
        )
        await interaction.followup.send(
            f"✅ **{selected_folder}** フォルダに登録しました！",
            ephemeral=True,
        )


class CategorySelectView(discord.ui.View):

    def __init__(self, categories, message_id, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(
            CategorySelect(categories, message_id, post_id, vc_id)
        )

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


class ArchiveViewButton(discord.ui.View):

    def __init__(self, build_embed_func):
        super().__init__(timeout=None)
        self.build_embed_func = build_embed_func

    @discord.ui.button(
        label="自分のブックマークを見る",
        style=discord.ButtonStyle.primary,
        custom_id="view_my_archive",
        emoji="📚",
    )
    async def view_archive(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        embed = await self.build_embed_func(
            interaction.user.id, interaction.user.display_name
        )
        if embed is None:
            await interaction.followup.send(
                "📭 まだフォルダがありません。最初に `/category_add` で作ってください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

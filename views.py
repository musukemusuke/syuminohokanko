import discord

class CategorySelect(discord.ui.Select):
    def __init__(self, categories, message, post_id, vc_id):
        self.orig_msg = message
        self.post_id = post_id
        self.vc_id = vc_id
        options = [
            discord.SelectOption(label=cat, description=f"「{cat}」に保存")
            for cat in categories
        ]
        super().__init__(placeholder="フォルダを選択...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        storage_vc = interaction.client.get_channel(self.vc_id)
        if not storage_vc: return

        saved_url = ""
        if self.orig_msg.attachments:
            for attachment in self.orig_msg.attachments:
                file_data = await attachment.to_file()
                backup_msg = await storage_vc.send(content="📦 BACKUP", file=file_data)
                saved_url = backup_msg.attachments.url
                break
        else:
            for word in self.orig_msg.content.split():
                if word.startswith("http"):
                    saved_url = word
                    break

        if saved_url:
            log_text = f"📁FOLDER:{self.values}\n👤USER:{interaction.user.id}\n🔗DATA:{saved_url}"
            await storage_vc.send(log_text)
            await interaction.followup.send(f"✅ **{self.values}** に保存しました！", ephemeral=True)

class CategorySelectView(discord.ui.View):
    def __init__(self, categories, message, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, message, post_id, vc_id))

class ArchiveViewButton(discord.ui.View):
    def __init__(self, build_embed_func):
        super().__init__(timeout=None)
        self.build_embed_func = build_embed_func

    @discord.ui.button(label="自分のブックマークを見る", style=discord.ButtonStyle.primary, custom_id="view_my_archive", emoji="📚")
    async def view_archive(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = await self.build_embed_func(interaction.user.id, interaction.user.display_name)
        if embed is None:
            await interaction.followup.send("📭 フォルダがありません。", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

import discord
import traceback

class CategorySelect(discord.ui.Select):
    def __init__(self, categories, original_urls, post_id, vc_id):
        self.original_urls = original_urls
        self.post_id = post_id
        self.vc_id = vc_id
        
        options = [
            discord.SelectOption(label=cat, emoji="📂", description=f"フォルダ 「{cat}」 へ格納")
            for cat in categories
        ]
        super().__init__(
            placeholder=" ── 保管先を選択してください ── ",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc: return

            selected_folder = self.values
            
            # 💡 【修正】MEMOとTIMEを完全にカットし、3項目のみを金庫に送信します
            for link in self.original_urls:
                await storage_vc.send(
                    f"📁FOLDER:{selected_folder}\n"
                    f"👤USER:{interaction.user.id}\n"
                    f"🔗LINK:{link}"
                )
            
            embed = discord.Embed(
                description=f"📥 フォルダ「**{selected_folder}**」へ正常にアーカイブしました。",
                color=0xd4af37
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            try: await interaction.message.delete()
            except: pass
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories, original_urls, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id))


class EphemeralTriggerButton(discord.ui.Button):
    def __init__(self, folders, url_list, post_id, storage_vc_id):
        super().__init__(label="フォルダを選択して保管", style=discord.ButtonStyle.blurple, emoji="📥")
        self.folders = folders
        self.url_list = url_list
        self.post_id = post_id
        self.storage_vc_id = storage_vc_id

    async def callback(self, interaction: discord.Interaction):
        view = CategorySelectView(self.folders, self.url_list, self.post_id, self.storage_vc_id)
        embed = discord.Embed(
            title="📥 URLの保管先を選択",
            description=f"対象のURL:\n{self.url_list}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
            color=0x2f3136
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EphemeralTriggerView(discord.ui.View):
    def __init__(self, folders, url_list, post_id, storage_vc_id):
        super().__init__(timeout=30)
        self.add_item(EphemeralTriggerButton(folders, url_list, post_id, storage_vc_id))

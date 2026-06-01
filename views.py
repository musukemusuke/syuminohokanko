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

            selected_folder = self.values if isinstance(self.values, list) else self.values
            timestamp = int(interaction.created_at.timestamp())

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
            
            # エフェメラルなのでメッセージの自動削除は不要（自動で消せるため）
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories, original_urls, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id))

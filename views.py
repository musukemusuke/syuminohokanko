import discord
import traceback

class CategorySelect(discord.ui.Select):
    # 💡 引数に folder_url_map を追加して受け取れるように拡張
    def __init__(self, categories, original_urls, post_id, vc_id, folder_url_map=None):
        self.original_urls = original_urls
        self.post_id = post_id
        self.vc_id = vc_id
        
        options = []
        for cat in categories:
            # 💡 【デザイン一新】そのフォルダに過去に入れた最新のURLを説明欄（description）にプレビュー表示
            desc_text = "保管されているデータがありません"
            if folder_url_map and cat in folder_url_map and folder_url_map[cat]:
                # 最新の保存URL（最初の1つ）を文字数制限に引っかからないようにカットして格納
                latest_url = folder_url_map[cat][0]
                desc_text = f"直近: {latest_url[:50]}"
                
            options.append(
                discord.SelectOption(
                    label=cat, 
                    emoji="📂", 
                    description=desc_text  # 💡 ここにフォルダに属するURL情報（履歴）が入ります
                )
            )
            
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

            selected_folder = self.values[0] if isinstance(self.values, list) else self.values

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
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories, original_urls, post_id, vc_id, folder_url_map=None):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id, folder_url_map))

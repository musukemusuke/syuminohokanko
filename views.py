import discord
import traceback

class CategorySelect(discord.ui.Select):
    # 💡 引数の順番を整理し、folder_url_map が無くても安全に動くように初期化をガード
    def __init__(self, categories, original_urls, post_id, vc_id, folder_url_map=None):
        self.original_urls = original_urls
        self.post_id = post_id
        self.vc_id = vc_id
        
        options = []
        for cat in categories:
            # 💡 【デザイン一新】そのフォルダに過去に入れた最新のURLを説明欄（description）にプレビュー表示
            desc_text = "保管されているデータがありません"
            if folder_url_map and isinstance(folder_url_map, dict) and cat in folder_url_map and folder_url_map[cat]:
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
            if not storage_vc: 
                await interaction.followup.send("❌ データ金庫のチャンネルが見つかりません。", ephemeral=True)
                return

            selected_folder = self.values[0] if isinstance(self.values, list) else self.values

            # URLリストをループして金庫へ格納
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
    # 💡 引数の数が4つでも5つでもエラーにならないように可変引数で安全に対処
    def __init__(self, categories, original_urls, post_id, vc_id, folder_url_map=None):
        super().__init__(timeout=60)
        # もし引数の位置がズレて folder_url_map に整数(vc_id)が入ってきた場合のディフェンス
        if isinstance(folder_url_map, int) or (folder_url_map is None and isinstance(vc_id, dict)):
            # 引数の位置を正しい位置に自動的にマッピングし直す
            real_vc_id = vc_id if isinstance(vc_id, int) else post_id
            real_folder_map = vc_id if isinstance(vc_id, dict) else None
            self.add_item(CategorySelect(categories, original_urls, post_id, real_vc_id, real_folder_map))
        else:
            self.add_item(CategorySelect(categories, original_urls, post_id, vc_id, folder_url_map))

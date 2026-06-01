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
        # 即座に通信を確保してタイムアウトを100%防止
        await interaction.response.defer(ephemeral=True)
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc: return

            selected_folder = self.values
            timestamp = int(interaction.created_at.timestamp())

            # 金庫VCへ生URLデータを格納
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
            
            # 仕分けが終わったら、最初にチャンネルに出たボタン付き案内メッセージを自動消去
            try: await interaction.message.delete()
            except: pass
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories, original_urls, post_id, vc_id):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id))


# 💡 【完全復活】ボタンを押したユーザーにだけ、100%確実にエフェメラルメニューを表示させる中継ボタン
class EphemeralTriggerButton(discord.ui.Button):
    def __init__(self, folders, url_list, post_id, storage_vc_id):
        super().__init__(label="フォルダを選択して保管", style=discord.ButtonStyle.blurple, emoji="📥")
        self.folders = folders
        self.url_list = url_list
        self.post_id = post_id
        self.storage_vc_id = storage_vc_id

    async def callback(self, interaction: discord.Interaction):
        # 💡 ボタンに対する「Interaction」が発生するため、100%確実にエフェメラル表示がDiscordに許可されます
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

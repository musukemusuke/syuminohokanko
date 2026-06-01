import discord
import traceback

class CategorySelect(discord.ui.Select):
    def __init__(self, categories, original_urls, post_id, vc_id, memo_text):
        self.original_urls = original_urls
        self.post_id = post_id
        self.vc_id = vc_id
        self.memo_text = memo_text
        
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
        # 即座にレスポンスを確保してタイムアウトを防止
        await interaction.response.defer(ephemeral=True)
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc: return

            selected_folder = self.values[0] if isinstance(self.values, list) else self.values
            timestamp = int(interaction.created_at.timestamp())

            # 金庫VCへ生URLデータを格納
            for link in self.original_urls:
                await storage_vc.send(
                    f"📁FOLDER:{selected_folder}\n"
                    f"👤USER:{interaction.user.id}\n"
                    f"🔗LINK:{link}\n"
                    f"📝MEMO:{self.memo_text}\n"
                    f"⏰TIME:{timestamp}"
                )
            
            embed = discord.Embed(
                description=f"📥 フォルダ「**{selected_folder}**」へ正常にアーカイブしました。",
                color=0xd4af37
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # 仕分けが終わったら、最初にチャンネルに出たボタン付き案内メッセージを自動削除
            try: await interaction.message.delete()
            except: pass
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):
    def __init__(self, categories, original_urls, post_id, vc_id, memo_text=""):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id, memo_text))


# トリガーボタン
class EphemeralTriggerButton(discord.ui.Button):
    def __init__(self, folders, url_list, post_id, storage_vc_id, memo_text):
        super().__init__(label="フォルダを選択して保管", style=discord.ButtonStyle.blurple, emoji="📥")
        self.folders = folders
        self.url_list = url_list
        self.post_id = post_id
        self.storage_vc_id = storage_vc_id
        self.memo_text = memo_text

    async def callback(self, interaction: discord.Interaction):
        # ボタンを押したユーザーにだけ見えるエフェメラル表示として、セレクトメニューを立ち上げる
        view = CategorySelectView(self.folders, self.url_list, self.post_id, self.storage_vc_id, self.memo_text)
        embed = discord.Embed(
            title="📥 URLの保管先を選択",
            description=f"対象のURL:\n{self.url_list[0]}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
            color=0x2f3136
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EphemeralTriggerView(discord.ui.View):
    def __init__(self, folders, url_list, post_id, storage_vc_id, memo_text=""):
        super().__init__(timeout=30)
        self.add_item(EphemeralTriggerButton(folders, url_list, post_id, storage_vc_id, memo_text))

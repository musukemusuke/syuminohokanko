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
        await interaction.response.defer(ephemeral=True)
        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc: return

            selected_folder = self.values
            timestamp = int(interaction.created_at.timestamp())

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
        except Exception as e:
            traceback.print_exc()


class CategorySelectView(discord.ui.View):

    def __init__(self, categories, original_urls, post_id, vc_id, memo_text=""):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, original_urls, post_id, vc_id, memo_text))


# 💡 【新設】bookmark.pyから文字数の多い処理をここに引き受けました
async def send_ephemeral_select_menu(bot, channel, folders, url_list, post_id, storage_vc_id, memo_text):
    try:
        view = CategorySelectView(reversed(folders), url_list, post_id, storage_vc_id, memo_text)
        embed = discord.Embed(
            title="📥 URLの保管先を選択",
            description=f"検出されたURL:\n{url_list}\n\nどのフォルダにアーカイブしますか？（あなただけに表示されています）",
            color=0x2f3136
        )
        # Webhookを生成してエフェメラルメッセージを配送
        webhook = await channel.create_webhook(name="Crystallizer")
        await webhook.send(
            embed=embed, 
            view=view, 
            ephemeral=True, 
            username=bot.user.name, 
            avatar_url=bot.user.display_avatar.url
        )
        await webhook.delete()
    except Exception as e:
        print(f"[ERROR] エフェメラルメニューの送信に失敗しました: {e}")

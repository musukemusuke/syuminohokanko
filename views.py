import discord
import traceback
from typing import List, Optional, Dict


class CategorySelect(discord.ui.Select):
    def __init__(
        self,
        categories: List[str],
        original_urls: List[str],
        post_id: int,
        vc_id: int,
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        self.original_urls = original_urls
        self.post_id = post_id
        self.vc_id = vc_id
        self.folder_url_map = folder_url_map or {}

        options = []
        for cat in categories:
            desc = "保管されているデータがありません"
            
            if cat in self.folder_url_map and self.folder_url_map[cat]:
                latest = self.folder_url_map[cat][0]
                # 安全に文字数制限
                desc = f"直近: {latest[:60]}" if len(latest) > 60 else f"直近: {latest}"

            options.append(
                discord.SelectOption(
                    label=cat[:80],      # labelも安全にカット
                    emoji="📂",
                    description=desc,
                )
            )

        super().__init__(
            placeholder="── 保管先フォルダを選択してください ──",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            storage_vc = interaction.client.get_channel(self.vc_id)
            if not storage_vc:
                return await interaction.followup.send(
                    "❌ データ金庫が見つかりません。", ephemeral=True
                )

            selected_folder = self.values[0]

            # 金庫に保存
            for link in self.original_urls:
                await storage_vc.send(
                    f"📁FOLDER:{selected_folder}\n"
                    f"👤USER:{interaction.user.id}\n"
                    f"🔗LINK:{link}"
                )

            embed = discord.Embed(
                description=f"✅ **{selected_folder}** にアーカイブしました。",
                color=0xd4af37,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Viewを無効化（二重送信防止）
            self.view.stop()
            await self.view.disable_all_items()

        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(
                "❌ 保存中にエラーが発生しました。", ephemeral=True
            )


class CategorySelectView(discord.ui.View):
    def __init__(
        self,
        categories: List[str],
        original_urls: List[str],
        post_id: int,
        vc_id: int,
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        super().__init__(timeout=90)  # 少し長めに
        self.add_item(
            CategorySelect(categories, original_urls, post_id, vc_id, folder_url_map)
        )

    async def on_timeout(self):
        """タイムアウト時にボタンを無効化"""
        await self.disable_all_items()

    async def disable_all_items(self):
        """全アイテムを無効化"""
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        # 必要なら元のメッセージを編集（ただしViewがどこに送られたかによる）

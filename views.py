import discord
import traceback
from typing import List, Dict, Optional, Union


class CategorySelect(discord.ui.Select):
    def __init__(
        self,
        categories: List[str],
        original_urls: List[str],
        post_id: int,
        target_dest: Union[discord.TextChannel, discord.Thread], # IDではなくオブジェクトを受け取る
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        self.original_urls = original_urls
        self.post_id = post_id
        self.target_dest = target_dest
        self.folder_url_map = folder_url_map or {}

        options = []
        for cat in categories:
            desc = "保管データなし"
            if cat in self.folder_url_map and self.folder_url_map[cat]:
                latest = self.folder_url_map[cat]
                desc = f"直近: {latest[:55]}" if len(latest) > 55 else f"直近: {latest}"

            options.append(
                discord.SelectOption(
                    label=cat[:80],
                    emoji="📂",
                    description=desc,
                )
            )

        super().__init__(
            placeholder="── 保存先フォルダを選択してください ──",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            if not self.target_dest:
                return await interaction.response.send_message("❌ 保存先スレッドの展開に失敗しました。", ephemeral=True)

            selected = self.values

            # プライベートスレッドへ直接安全にログを書き込み
            for link in self.original_urls:
                await self.target_dest.send(
                    f"FOLDER:{selected}\n"
                    f"USER:{interaction.user.id}\n"
                    f"LINK:{link}"
                )

            embed = discord.Embed(
                description=f"✅ **{selected}** に保存しました。",
                color=0xd4af37
            )
            
            self.view.stop()
            for item in self.view.children:
                if hasattr(item, "disabled"):
                    item.disabled = True

            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception:
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ 保存中にエラーが発生しました。", ephemeral=True)
            else:
                await interaction.followup.send("❌ 保存中にエラーが発生しました。", ephemeral=True)


class CategorySelectView(discord.ui.View):
    def __init__(
        self,
        categories: List[str],
        original_urls: List[str],
        post_id: int,
        target_dest: Union[discord.TextChannel, discord.Thread],
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        super().__init__(timeout=120)
        self.message: Optional[discord.Message] = None
        self.add_item(CategorySelect(categories, original_urls, post_id, target_dest, folder_url_map))

    async def on_timeout(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

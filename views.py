import discord
import traceback
from typing import List, Dict, Optional


class CategorySelect(discord.ui.Select):
    def __init__(
        self,
        categories: List[str],
        original_urls: List[str],
        post_id: int,
        channel_id: int,  # 変数名を vc_id から channel_id に変更
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        self.original_urls = original_urls
        self.post_id = post_id
        self.channel_id = channel_id
        self.folder_url_map = folder_url_map or {}

        options = []
        for cat in categories:
            desc = "保管データなし"
            if cat in self.folder_url_map and self.folder_url_map[cat]:
                latest = self.folder_url_map[cat][0]
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
        # メッセージの更新と追加応答を両方行うため、ここでは defer せず後で処理します
        try:
            storage_channel = interaction.client.get_channel(self.channel_id)
            if not storage_channel:
                return await interaction.response.send_message("❌ データ金庫が見つかりません。", ephemeral=True)

            selected = self.values[0]

            # 【修正】パース関数（_parse_log）が正しく読める形式（キーに絵文字を入れない）で送信
            for link in self.original_urls:
                await storage_channel.send(
                    f"FOLDER:{selected}\n"
                    f"USER:{interaction.user.id}\n"
                    f"LINK:{link}"
                )

            embed = discord.Embed(
                description=f"✅ **{selected}** に保存しました。",
                color=0xd4af37
            )
            
            # 【修正】Viewのコンポーネントを無効化
            self.view.stop()
            for item in self.view.children:
                if hasattr(item, "disabled"):
                    item.disabled = True

            # 【重要】元のメッセージのViewを更新してグレーアウトさせつつ、ユーザーへ保存完了を通知
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception:
            traceback.print_exc()
            # エラー時も安全に応答
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
        channel_id: int,
        folder_url_map: Optional[Dict[str, List[str]]] = None,
    ):
        super().__init__(timeout=120)
        self.message: Optional[discord.Message] = None  # タイムアウト時の編集用に保持
        self.add_item(CategorySelect(categories, original_urls, post_id, channel_id, folder_url_map))

    async def on_timeout(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        # もし呼び出し元で view.message = await ctx.send(...) のようにメッセージを渡していれば、タイムアウト時に自動でグレーアウト
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


### 🔄 連動する読み込み側（_parse_log用）の新規フォルダ作成（NEW_FOLDER）時の推奨フォーマット
# もし別ファイルで「新規フォルダ作成」のログを送信している処理がある場合は、
# 以下のように絵文字をコロンの左側に含めないように統一してください。
# 例：
# f"NEW_FOLDER:{folder_name}\nUSER:{user_id}\nLINK:{rep_link}"

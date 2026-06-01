import asyncio
import re
import discord
from discord.ext import commands

# 【修正】状態管理用の関数を commands.py から確実にインポートする
from cogs.commands import get_guild_data
from views import CategorySelectView

class ListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ボット自身のメッセージ、またはDMは無視
        if message.author.bot or not message.guild:
            return

        # CommandsCogからデータ取得
        commands_cog = self.bot.get_cog("CommandsCog")
        if not commands_cog:
            return

        # インポートした関数でサーバーごとの状態管理データを取得
        data = get_guild_data(message.guild.id)

        # チャンネルIDがキャッシュになければ動的にロード
        if not data["post_id"]:
            commands_cog.load_channel_ids(message.guild)

        # ブックマーク受付チャンネル以外はスルー
        if message.channel.id != data["post_id"]:
            return

        # メッセージ内からURL（リンク）を正規表現で探す
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match:
            return

        # ログ金庫のチャンネルオブジェクトを取得
        storage_channel = self.bot.get_channel(data["storage_channel_id"])
        if not storage_channel:
            return

        # 【修正】ボット再起動対策：commands.pyに実装した過去ログからのフォルダ自動復元関数を呼び出す
        folders = await commands_cog.sync_user_folders_from_history(storage_channel, message.author.id)
        data["folders"][message.author.id] = folders

        # フォルダが1つもない場合は警告して10秒後にメッセージを消す
        if not folders:
            await message.reply("❌ まだフォルダがありません。先に `/category_add` でフォルダを作成してください。", delete_after=10)
            return

        # ユーザーが貼った生のURLメッセージを削除（チャンネルを綺麗に保つため）
        try:
            await message.delete()
        except discord.Forbidden:
            print("⚠️ メッセージの削除権限（メッセージの管理）がボットにありません。")
        except discord.NotFound:
            pass

        # 【修正】引数の渡し方を修正（storage_channel_id を渡す、reversedをlistにする）
        view = CategorySelectView(
            categories=list(reversed(folders)), 
            original_urls=[url_match.group(0)], 
            post_id=data["post_id"], 
            channel_id=data["storage_channel_id"]
        )
        
        embed = discord.Embed(
            title="📥 保存先フォルダを選択してください", 
            description=f"**投稿者:** {message.author.mention}\n**URL:**\n{url_match.group(0)}", 
            color=0x2f3136
        )
        
        # メッセージを送信（ephemeralが使えないチャンネル送信なので、delete_afterで自動消去を設定）
        sent_message = await message.channel.send(embed=embed, view=view, delete_after=90)
        
        # 【修正】View側に送信したメッセージを記憶させ、タイムアウト時に正常にグレーアウトできるようにする
        view.message = sent_message

async def setup(bot):
    await bot.add_cog(ListenerCog(bot))

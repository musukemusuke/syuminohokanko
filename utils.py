import discord
import traceback

async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        print("[WARNING] utils.build_archive_embed: 金庫チャンネルが見つかりません。")
        return None

    folders = []
    archive_data = {}

    try:
        # 金庫チャンネルから履歴を取得（最新のデータから順に解析）
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
            # --- 1. 新規フォルダ作成ログの解析 ---
            if content.startswith("🆕NEW_FOLDER:"):
                try:
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"):
                            f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                    
                    if f_name and u_id_text:
                        u_id = int(u_id_text)
                        if u_id == user_id and f_name not in folders:
                            folders.append(f_name)
                            if f_name not in archive_data:
                                archive_data[f_name] = []
                except Exception as e:
                    continue
                    
            # --- 2. フォルダ保存ログの解析 ---
            elif content.startswith("📁FOLDER:"):
                try:
                    f_name, u_id_text, link = None, None, None
                    for line in lines:
                        if line.startswith("📁FOLDER:"):
                            f_name = line.replace("📁FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                        elif line.startswith("🔗LINK:"):
                            link = line.replace("🔗LINK:", "").strip()
                            
                    if f_name and u_id_text and link:
                        u_id = int(u_id_text)
                        if u_id == user_id:
                            if f_name not in archive_data:
                                archive_data[f_name] = []
                            # 新しいリンクのみをリストに追加（重複防止）
                            if link not in archive_data[f_name]:
                                archive_data[f_name].append(link)
                except Exception as e:
                    continue

    except Exception as e:
        print("[ERROR] utils.build_archive_embed: 履歴の解析中に致命的なエラーが発生しました:")
        traceback.print_exc()
        return None

    # ユーザーのフォルダが1つもない場合は画面を作らない
    if not folders:
        return None

    # 埋め込み（Embed）の構築
    embed = discord.Embed(
        title=f"📚 {display_name} のブックマーク一覧",
        description="リンク（青い文字）をクリックすると、保存した動画や画像のメッセージに直接ジャンプできます。",
        color=discord.Color.blue(),
    )
    
    # フォルダを作成された順（古い順、あるいはreversedで調整）に表示
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_list = (
            "\n".join(
                [
                    f"• [保存したデータを見に行く（ここをクリック）]({item})"
                    for item in items
                ]
            )
            if items
            else "*（まだデータが登録されていません）*"
        )
        embed.add_field(name=f"📁 {folder}", value=item_list, inline=False)

    return embed

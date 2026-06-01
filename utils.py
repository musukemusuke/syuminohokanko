import discord
import traceback

async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders = []
    archive_data = {}
    deleted_folders = []

    try:
        # 最新のメッセージから履歴を追う
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
            # 削除ログの先行回収
            if content.startswith("🗑️DELETE_FOLDER:"):
                try:
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🗑️DELETE_FOLDER:"):
                            f_name = line.replace("🗑️DELETE_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                    if f_name and u_id_text and int(u_id_text) == user_id:
                        deleted_folders.append(f_name)
                except:
                    continue

            elif content.startswith("🆕NEW_FOLDER:"):
                try:
                    f_name, u_id_text = None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"):
                            f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                    
                    if f_name and u_id_text:
                        if int(u_id_text) == user_id and f_name not in folders:
                            if f_name not in deleted_folders:
                                folders.append(f_name)
                                if f_name not in archive_data:
                                    archive_data[f_name] = []
                except:
                    continue
                    
            elif content.startswith("📁FOLDER:"):
                try:
                    f_name, u_id_text, link, memo, timestamp = None, None, None, "", ""
                    for line in lines:
                        if line.startswith("📁FOLDER:"):
                            f_name = line.replace("📁FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                        elif line.startswith("🔗LINK:"):
                            link = line.replace("🔗LINK:", "").strip()
                        elif line.startswith("📝MEMO:"):
                            memo = line.replace("📝MEMO:", "").strip()
                        elif line.startswith("⏰TIME:"):
                            timestamp = line.replace("⏰TIME:", "").strip()
                            
                    if f_name and u_id_text and link:
                        if int(u_id_text) == user_id and f_name not in deleted_folders:
                            if f_name not in archive_data:
                                    archive_data[f_name] = []
                            data_tuple = (link, memo, timestamp)
                            if data_tuple not in archive_data[f_name]:
                                archive_data[f_name].append(data_tuple)
                except:
                    continue

    except Exception as e:
        traceback.print_exc()
        return None

    # 有効なフォルダがなければ非表示
    folders = [f for f in folders if f not in deleted_folders]
    if not folders:
        return None

    embed = discord.Embed(
        title=f"⚜️ {display_name} | COLLECTION ARCHIVE",
        description="保存されたデータカードです。リンクから直接コンテンツへアクセスできます。",
        color=0x2f3136
    )
    
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_links = []
        
        for item in items:
            link, memo, timestamp = item
            
            if "://discord.com" in link:
                text = "📝 NOTE"
            elif any(ext in link.lower() for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                text = "🖼️ IMAGE"
            elif any(ext in link.lower() for ext in [".mp4", ".mov", ".mkv", ".webm"]):
                text = "🎬 VIDEO"
            else:
                text = "🔗 LINK"
            
            time_display = f" ── <t:{timestamp}:R>" if timestamp else ""
            memo_display = f" \n   └ *{memo[:20]}...*" if (memo and "ファイル合計" not in memo and len(memo) > 1) else ""
            
            item_links.append(f"▪️ [{text}]({link}){time_display}{memo_display}")
            
        item_list = "\n".join(item_links) if item_links else "*（空のフォルダです）*"
        embed.add_field(name=f"📂 {folder}", value=item_list, inline=False)

    return embed


# 💡 【必須の関数】指定したキーワードで過去のアイテムを掘り起こすロジック
async def search_archive_data(bot, vc_id, user_id, keyword):
    storage_vc = bot.get_channel(vc_id)
    embed = discord.Embed(
        title=f"🔍 「{keyword}」 の検索結果",
        color=0xd4af37
    )
    
    if not storage_vc:
        embed.description = "❌ 金庫への同期に失敗しました。"
        return embed

    found_count = 0
    results_text = []
    deleted_folders = []

    try:
        # 先に削除フォルダリストを精査
        async for msg in storage_vc.history(limit=1000):
            if msg.content.startswith("🗑️DELETE_FOLDER:"):
                lines = msg.content.split("\n")
                f_name, u_id_text = None, None
                for line in lines:
                    if line.startswith("🗑️DELETE_FOLDER:"):
                        f_name = line.replace("🗑️DELETE_FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id_text = line.replace("👤USER:", "").strip()
                if f_name and u_id_text and int(u_id_text) == user_id:
                    deleted_folders.append(f_name)

        # 検索データの抽出
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            if content.startswith("📁FOLDER:"):
                lines = content.split("\n")
                f_name, u_id_text, link, memo, timestamp = None, None, None, "", ""
                
                for line in lines:
                    if line.startswith("📁FOLDER:"):
                        f_name = line.replace("📁FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id_text = line.replace("👤USER:", "").strip()
                    elif line.startswith("🔗LINK:"):
                        link = line.replace("🔗LINK:", "").strip()
                    elif line.startswith("📝MEMO:"):
                        memo = line.replace("📝MEMO:", "").strip()
                    elif line.startswith("⏰TIME:"):
                        timestamp = line.replace("⏰TIME:", "").strip()

                if f_name and u_id_text and link and (f_name not in deleted_folders):
                    if int(u_id_text) == user_id:
                        if (keyword.lower() in f_name.lower()) or (keyword.lower() in link.lower()) or (keyword.lower() in memo.lower()):
                            time_display = f"<t:{timestamp}:R>" if timestamp else "不明"
                            results_text.append(
                                f"📂 **{f_name}** ({time_display})\n"
                                f" └─ [対象を開く]({link}) " + (f"| *{memo}*" if memo else "")
                            )
                            found_count += 1
                            if found_count >= 15:
                                break
    except:
        pass

    if found_count == 0:
        embed.description = f"該当するアーカイブは見つかりませんでした。"
        embed.color = 0x555555
    else:
        embed.description = f"一致したアイテムが {found_count} 件見つかりました。\n\n" + "\n\n".join(results_text)

    return embed


# 💡 【必須の関数】金庫にフォルダ削除のログを刻むための関数
async def delete_category_logs(bot, vc_id, user_id, folder_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return False

    exist = False
    async for msg in storage_vc.history(limit=1000):
        if msg.content.startswith("🆕NEW_FOLDER:"):
            lines = msg.content.split("\n")
            f_name, u_id_text = None, None
            for line in lines:
                if line.startswith("🆕NEW_FOLDER:"):
                    f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                elif line.startswith("👤USER:"):
                    u_id_text = line.replace("👤USER:", "").strip()
            if f_name == folder_name and int(u_id_text) == user_id:
                exist = True
                break

    if exist:
        await storage_vc.send(f"🗑️DELETE_FOLDER:{folder_name}\n👤USER:{user_id}")
        return True
    return False

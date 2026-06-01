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
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
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

    folders = [f for f in folders if f not in deleted_folders]
    if not folders:
        return None

    embed = discord.Embed(
        title=f"⚜️ {display_name} | COLLECTION ARCHIVE",
        color=0x2f3136
    )
    
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_links = []
        
        for item in items:
            link, memo, timestamp = item
            
            # ドメインに応じて文字のラベルをスマートに切り替える
            if "youtube.com" in link.lower() or "youtu.be" in link.lower():
                text = "🎬 YOUTUBE VIDEO"
            elif "x.com" in link.lower() or "twitter.com" in link.lower():
                text = "🖼️ X (TWITTER)"
            else:
                text = "🔗 LINK"
            
            time_display = f" ── <t:{timestamp}:R>" if timestamp else ""
            
            # 💡 【完全修正】下の段のむき出しの長い生URL（\n └─ https://...）を完全に消去しました。
            # 上の段の青くてスッキリしたハイパーリンクだけを格納します。
            item_links.append(f"▪️ [{text}]({link}){time_display}")
            
        item_list = "\n".join(item_links) if item_links else "*（空のフォルダです）*"
        embed.add_field(name=f"📂 {folder}", value=item_list, inline=False)

    return embed


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
                            # 💡 検索結果側からも下の生URLを消去し、青いリンクだけに統一
                            results_text.append(
                                f"📂 **{f_name}** ({time_display})\n"
                                f" └─ [LINK]({link})"
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

import discord
import traceback

async def build_archive_embed(bot, vc_id, user_id, display_name):
    storage_vc = bot.get_channel(vc_id)
    if not storage_vc:
        return None

    folders = []
    folder_urls = {} # {folder_name: folder_top_url}
    archive_data = {}

    try:
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
            if content.startswith("🆕NEW_FOLDER:"):
                try:
                    f_name, u_id_text, f_url = None, None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"):
                            f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                        elif line.startswith("🔗LINK:"):
                            f_url = line.replace("🔗LINK:", "").strip()
                    
                    if f_name and u_id_text:
                        if int(u_id_text) == user_id and f_name not in folders:
                            folders.append(f_name)
                            if f_url:
                                folder_urls[f_name] = f_url
                            if f_name not in archive_data:
                                archive_data[f_name] = []
                except:
                    continue
                    
            elif content.startswith("📁FOLDER:"):
                try:
                    f_name, u_id_text, link = None, None, None
                    for line in lines:
                        if line.startswith("📁FOLDER:"):
                            raw_f = line.replace("📁FOLDER:", "").strip()
                            if raw_f.startswith("[") and raw_f.endswith("]"): raw_f = raw_f[1:-1].strip()
                            if (raw_f.startswith("'") and raw_f.endswith("'")) or (raw_f.startswith('"') and raw_f.endswith('"')): raw_f = raw_f[1:-1].strip()
                            f_name = raw_f
                        elif line.startswith("👤USER:"):
                            u_id_text = line.replace("👤USER:", "").strip()
                        elif line.startswith("🔗LINK:"):
                            link = line.replace("🔗LINK:", "").strip()
                            
                    if f_name and u_id_text and link:
                        if int(u_id_text) == user_id:
                            if f_name not in archive_data:
                                archive_data[f_name] = []
                            if link not in archive_data[f_name]:
                                archive_data[f_name].append(link)
                except:
                    continue

    except Exception as e:
        traceback.print_exc()
        return None

    if not folders:
        return None

    embed = discord.Embed(
        title=f"📚 {display_name} の趣味の保管庫",
        description="これまでに集めたURLリンクの一覧です。",
        color=0x2f3136
    )
    
    for folder in reversed(folders):
        items = archive_data.get(folder, [])
        item_links = []
        
        # 💡 もしフォルダ自体に代表URLが登録されていれば、リストの先頭にわかりやすく配置
        if folder in folder_urls:
            item_links.append(f"⭐ **代表リンク:** {folder_urls[folder]}")
            if items:
                item_links.append("──────") # 区切り線
        
        for link in items:
            item_links.append(f"{link}")
            
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

    try:
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            if content.startswith("📁FOLDER:"):
                lines = content.split("\n")
                f_name, u_id_text, link = None, None, None
                
                for line in lines:
                    if line.startswith("📁FOLDER:"):
                        f_name = line.replace("📁FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id_text = line.replace("👤USER:", "").strip()
                    elif line.startswith("🔗LINK:"):
                        link = line.replace("🔗LINK:", "").strip()

                if f_name and u_id_text and link:
                    if int(u_id_text) == user_id:
                        if (keyword.lower() in f_name.lower()) or (keyword.lower() in link.lower()):
                            results_text.append(
                                f"📂 **{f_name}**\n"
                                f" └─ {link}"
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

    deleted_any = False
    try:
        async for msg in storage_vc.history(limit=1000):
            content = msg.content
            lines = content.split("\n")
            
            if content.startswith("🆕NEW_FOLDER:"):
                f_name, u_id_text = None, None
                for line in lines:
                    if line.startswith("🆕NEW_FOLDER:"):
                        f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id_text = line.replace("👤USER:", "").strip()
                
                if f_name == folder_name and u_id_text and int(u_id_text) == user_id:
                    await msg.delete()
                    deleted_any = True
                    
            elif content.startswith("📁FOLDER:"):
                f_name, u_id_text = None, None
                for line in lines:
                    if line.startswith("📁FOLDER:"):
                        f_name = line.replace("📁FOLDER:", "").strip()
                    elif line.startswith("👤USER:"):
                        u_id_text = line.replace("👤USER:", "").strip()
                
                if u_id_text and int(u_id_text) == user_id and (folder_name in f_name):
                    await msg.delete()
                    deleted_any = True
                    
    except Exception as e:
        print(f"[ERROR] 金庫データの物理削除中にエラーが発生しました: {e}")
        return False

    return deleted_any

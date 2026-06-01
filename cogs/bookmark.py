    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        global post_id, storage_vc_id
        if message.author.bot or (message.guild and (not post_id or not storage_vc_id) and not load_channel_ids(message.guild)): return
        if message.channel.id != post_id: return

        # 💡 URLの抽出判定
        url_match = re.search(r"https?://[^\s]+", message.content)
        if not url_match: return

        url_list, memo_text, user_id = [url_match.group(0)], message.content.strip(), message.author.id
        folders, deleted_folders = [], []

        # 💡 フォルダ一覧の取得
        try:
            storage_vc = self.bot.get_channel(storage_vc_id)
            async for msg in storage_vc.history(limit=1000):
                content = msg.content
                lines = content.split("\n")
                if content.startswith("🆕NEW_FOLDER:"):
                    f_name, u_id = None, None
                    for line in lines:
                        if line.startswith("🆕NEW_FOLDER:"): f_name = line.replace("🆕NEW_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"): u_id = line.replace("👤USER:", "").strip()
                    if f_name and u_id and int(u_id) == user_id:
                        f_name = clean_folder_name(f_name)
                        if f_name not in folders: folders.append(f_name)
                elif content.startswith("🗑️DELETE_FOLDER:"):
                    f_name, u_id = None, None
                    for line in lines:
                        if line.startswith("🗑️DELETE_FOLDER:"): f_name = line.replace("🗑️DELETE_FOLDER:", "").strip()
                        elif line.startswith("👤USER:"): u_id = line.replace("👤USER:", "").strip()
                    if f_name and u_id and int(u_id) == user_id:
                        f_name = clean_folder_name(f_name)
                        deleted_folders.append(f_name)
        except: pass

        folders = [f for f in folders if f not in deleted_folders]
        if not folders: return

        # 💡 元のメッセージを即座に削除
        try: await message.delete()
        except: pass

        # 💡 【処理の分離】views.py 側に新設した関数へ丸投げしてエフェメラル送信
        from views import send_ephemeral_select_menu
        self.bot.loop.create_task(send_ephemeral_select_menu(self.bot, message.channel, folders, url_list, post_id, storage_vc_id, memo_text))

        # 💡 画面自動リフレッシュ
        async def refresh_task():
            await asyncio.sleep(2)
            await self.update_archive_channel_embed(message.guild, message.author.id, message.author.display_name)
        self.bot.loop.create_task(refresh_task())

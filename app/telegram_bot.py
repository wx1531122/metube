import logging
import asyncio
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

log = logging.getLogger('telegram_bot')

class TelegramBot:
    def __init__(self, token, allowed_user_ids, download_queue):
        self.token = token
        self.allowed_user_ids = [int(uid.strip()) for uid in allowed_user_ids.split(',') if uid.strip()] if allowed_user_ids else []
        self.download_queue = download_queue
        self.application = None
        self.running = False

    async def start(self):
        if not self.token:
            log.warning("Telegram Bot Token not provided. Telegram Bot will not start.")
            return

        log.info("Starting Telegram Bot...")
        self.application = ApplicationBuilder().token(self.token).build()

        handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        self.application.add_handler(handler)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self.running = True
        log.info("Telegram Bot started.")

    async def stop(self):
        if self.running and self.application:
            log.info("Stopping Telegram Bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.running = False
            log.info("Telegram Bot stopped.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id

        # Security Check:
        # If allowed_user_ids is empty, NO ONE is allowed.
        # If it is populated, only those IDs are allowed.
        if not self.allowed_user_ids:
            log.warning(f"Telegram message received from {user_id}, but TELEGRAM_ALLOWED_USER_IDS is empty. Ignoring message.")
            # Optionally reply to the user that the bot is not configured
            # await update.message.reply_text("Bot is not configured to accept commands.")
            return

        if user_id not in self.allowed_user_ids:
            log.warning(f"Unauthorized access attempt from user ID: {user_id}")
            return

        text = update.message.text
        # Extract URL (simple regex, can be improved)
        url_match = re.search(r'(https?://\S+)', text)

        if url_match:
            url = url_match.group(1)
            log.info(f"Received URL from Telegram: {url}")

            try:
                # Use default download options
                status = await self.download_queue.add(
                    url=url,
                    quality='best',
                    format='any',
                    folder=None,
                    custom_name_prefix='',
                    playlist_item_limit=0, # 0 = no limit (or uses config default depending on implementation)
                    auto_start=True
                )

                if status.get('status') == 'ok':
                    await update.message.reply_text(f"Download added: {url}")
                else:
                    await update.message.reply_text(f"Failed to add download: {status.get('msg', 'Unknown error')}")
            except Exception as e:
                log.error(f"Error adding download from Telegram: {e}")
                await update.message.reply_text("An internal error occurred while processing your request.")
        else:
            await update.message.reply_text("No valid URL found in your message.")

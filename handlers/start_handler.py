"""
Callback query handler for inline buttons (adapted for new upload flow)
"""

import os
import logging
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session, clear_user_session # clear_user_session को भी इम्पोर्ट करें
from bot.config import Config
from database.users_db import get_user_count # केवल stats के लिए आवश्यक है
from utils.upload_utils import upload_large_file, upload_to_telegram

LOGGER = logging.getLogger(__name__)

@bot_client.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    """Handle callback queries from inline keyboards and post-merge upload choices"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    user_first_name = callback_query.from_user.first_name
    
    LOGGER.info(f"User {user_id} ({user_first_name}) triggered callback: {data}")

    # Post-merge upload options
    if data.startswith("upload:"):
        await callback_query.answer("Processing upload request...", show_alert=False) # UX improvement
        try:
            _, method, merged_path = data.split(":", 2)
        except ValueError: # Changed to ValueError for more specific error
            await callback_query.message.edit_text("❓ Malformed upload action! Please try again.")
            LOGGER.error(f"Malformed upload callback data: {data} for user {user_id}")
            return

        if not merged_path or not os.path.exists(merged_path):
            await callback_query.message.edit_text("❌ Merged file not found or already deleted. Please merge again.")
            await callback_query.answer("❌ File missing or inaccessible!", show_alert=True)
            LOGGER.warning(f"Merged file {merged_path} not found for user {user_id}")
            return

        success = False
        if method == "tg":
            try:
                await callback_query.message.edit_text("📤 Uploading to Telegram… Please wait.")
                await upload_to_telegram(
                    client=client,
                    chat_id=user_id,
                    file_path=merged_path,
                    status_message=callback_query.message,
                    custom_filename="merged_video" # Custom filename from Config या session से लेना भी बेहतर हो सकता है
                )
                success = True
            except Exception as e:
                LOGGER.error(f"Telegram upload failed for user {user_id}: {e}", exc_info=True)
                await callback_query.message.edit_text(f"❌ Telegram upload failed: {e}")
        elif method == "gofile":
            try:
                await callback_query.message.edit_text("☁️ Uploading to GoFile… This might take a while.")
                link = await upload_large_file(merged_path, callback_query.message)
                if link:
                    await callback_query.message.edit_text(f"✅ GoFile link: {link}")
                    success = True
                else:
                    await callback_query.message.edit_text("❌ GoFile upload failed. Please try again.")
            except Exception as e:
                LOGGER.error(f"GoFile upload failed for user {user_id}: {e}", exc_info=True)
                await callback_query.message.edit_text(f"❌ GoFile upload failed: {e}")
        else:
            await callback_query.message.edit_text("❓ Unknown upload target! Please contact support.")
            LOGGER.warning(f"Unknown upload method '{method}' for user {user_id}")
            
        # Optional: Clean up merged file after successful upload
        if success and os.path.exists(merged_path):
            try:
                os.remove(merged_path)
                LOGGER.info(f"Cleaned up merged file: {merged_path} for user {user_id}")
            except OSError as e:
                LOGGER.error(f"Failed to delete merged file {merged_path}: {e}")
        return

    # Standard bot navigation and actions
    if data == "help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])
        
        help_text = Config.HELP_TEXT if hasattr(Config, 'HELP_TEXT') else "This bot helps you merge multiple videos. Send me videos to start!"
        
        await callback_query.message.edit_text(
            help_text,
            reply_markup=keyboard
        )
        await callback_query.answer("Displaying help information.")

    elif data == "start":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🆘 Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats")
            ],
            [
                InlineKeyboardButton("👨‍💻 Developer", url=Config.DEVELOPER_URL if hasattr(Config, 'DEVELOPER_URL') else "https://t.me/AbirHasan2005"),
                InlineKeyboardButton("📢 Updates", url=Config.UPDATES_CHANNEL_URL if hasattr(Config, 'UPDATES_CHANNEL_URL') else "https://t.me/Discovery_Updates")
            ]
        ])

        start_text = Config.START_TEXT if hasattr(Config, 'START_TEXT') else "👋 Hello! I am a video merger bot. Send me videos to merge them."
        
        await callback_query.message.edit_text(
            start_text,
            reply_markup=keyboard
        )
        await callback_query.answer("Back to main menu.")

    elif data == "stats":
        total_users = await get_user_count()

        stats_text = f"""
📊 **Bot Statistics**

👥 **Total Users:** `{total_users}`
🤖 **Bot Version:** `2.0`
⚡ **Status:** Active ✅

Bot is working perfectly!
"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])

        await callback_query.message.edit_text(
            stats_text,
            reply_markup=keyboard
        )
        await callback_query.answer("Displaying bot statistics.")

    elif data == "merge_videos":
        session = get_user_session(user_id)

        if len(session["videos"]) < 2:
            await callback_query.answer("❌ You need at least 2 videos to merge!", show_alert=True)
            return

        if session["merge_in_progress"]:
            await callback_query.answer("⏳ Merge already in progress!", show_alert=True)
            return

        await callback_query.answer("🎬 Starting merge process... This might take a moment.", show_alert=False)

        # Import here to avoid circular imports. This pattern is acceptable if carefully managed.
        try:
            from handlers.merge_handler import start_merge_process
            await start_merge_process(client, callback_query.message)
        except ImportError:
            LOGGER.error("Merge handler not found. Circular import issue?", exc_info=True)
            await callback_query.message.reply_text("❌ Merge functionality is temporarily unavailable. Please try again later.")
        except Exception as e:
            LOGGER.error(f"Error starting merge process for user {user_id}: {e}", exc_info=True)
            await callback_query.message.reply_text(f"❌ An error occurred during merge: {e}")

    elif data == "clear_videos":
        session = get_user_session(user_id)
        video_count = len(session["videos"])
        
        # Use the centralized clear_user_session function
        clear_user_session(user_id)

        await callback_query.message.edit_text(
            f"🗑 **Cleared Successfully!**\n\n"
            f"Removed {video_count} videos from queue. You can start fresh now!"
        )
        await callback_query.answer("✅ Videos queue cleared!")

    else:
        await callback_query.answer("❓ Unknown action!", show_alert=True)
        LOGGER.warning(f"Unknown callback data '{data}' from user {user_id}")

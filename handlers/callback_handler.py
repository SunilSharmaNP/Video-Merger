"""
Callback query handler for inline buttons (adapted for new upload flow)
"""

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session
from bot.config import Config
from database.users_db import get_user_count
from utils.upload_utils import upload_large_file, upload_to_telegram

@bot_client.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    """Handle callback queries from inline keyboards and post-merge upload choices"""
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Post-merge upload options
    if data.startswith("upload:"):
        # Format: upload:tg:<merged_path> OR upload:gofile:<merged_path>
        try:
            _, method, merged_path = data.split(":", 2)
        except Exception:
            await callback_query.answer("❓ Malformed upload action!", show_alert=True)
            return

        if not merged_path or not os.path.exists(merged_path):
            await callback_query.message.edit_text("❌ Merged file not found.")
            await callback_query.answer("❌ File missing!", show_alert=True)
            return

        if method == "tg":
            await callback_query.message.edit_text("📤 Uploading to Telegram…")
            await upload_to_telegram(
                client=client,
                chat_id=user_id,
                file_path=merged_path,
                status_message=callback_query.message,
                custom_filename="merged_video"
            )
        elif method == "gofile":
            await callback_query.message.edit_text("☁️ Uploading to GoFile…")
            link = await upload_large_file(merged_path, callback_query.message)
            if link:
                await callback_query.message.edit_text(f"✅ GoFile link: {link}")
            else:
                await callback_query.message.edit_text("❌ GoFile upload failed.")
        else:
            await callback_query.answer("❓ Unknown upload target!", show_alert=True)
        return

    # Standard bot navigation and actions
    if data == "help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])

        await callback_query.message.edit_text(
            Config.HELP_TEXT,
            reply_markup=keyboard
        )

    elif data == "start":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🆘 Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats")
            ],
            [
                InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/AbirHasan2005"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/Discovery_Updates")
            ]
        ])

        await callback_query.message.edit_text(
            Config.START_TEXT,
            reply_markup=keyboard
        )

    elif data == "stats":
        total_users = await get_user_count()

        stats_text = f"""
📊 **Bot Statistics**

👥 **Total Users:** {total_users}
🤖 **Bot Version:** 2.0
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

    elif data == "merge_videos":
        session = get_user_session(user_id)

        if len(session["videos"]) < 2:
            await callback_query.answer("❌ You need at least 2 videos to merge!", show_alert=True)
            return

        if session["merge_in_progress"]:
            await callback_query.answer("⏳ Merge already in progress!", show_alert=True)
            return

        await callback_query.answer("🎬 Starting merge process...")

        # Import here to avoid circular imports
        try:
            from handlers.merge_handler import start_merge_process
            await start_merge_process(client, callback_query.message)
        except ImportError:
            await callback_query.message.reply_text("❌ Merge functionality not available yet.")

    elif data == "clear_videos":
        session = get_user_session(user_id)
        video_count = len(session["videos"])
        session["videos"].clear()

        await callback_query.message.edit_text(
            f"🗑 **Cleared Successfully!**\n\n"
            f"Removed {video_count} videos from queue. You can start fresh now!"
        )

        await callback_query.answer("✅ Videos cleared!")

    else:
        await callback_query.answer("❓ Unknown action!", show_alert=True)

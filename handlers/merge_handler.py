"""
Enhanced merge handler with post-merge upload choice (Telegram or GoFile)
"""

import os
import asyncio
import time
import logging # Logging इम्पोर्ट करें
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.client import bot_client, get_user_session, clear_user_session # clear_user_session भी उपयोगी हो सकता है
from bot.config import Config
from utils.file_utils import download_from_tg, download_from_url, clean_temp_files
from utils.ffmpeg_utils import merge_videos
from utils.upload_utils import upload_large_file, upload_to_telegram

LOGGER = logging.getLogger(__name__) # Logger इनिशियलाइज़ करें

@bot_client.on_message(filters.command("merge") & filters.private)
async def merge_command(client, message: Message):
    """Handle /merge command: initiates the video merge process."""
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    LOGGER.info(f"User {user_id} ({user_first_name}) sent /merge command.")

    session = get_user_session(user_id)
    
    if len(session["videos"]) < 2:
        await message.reply_text(
            "❌ You need at least 2 videos to merge. Please send more videos first.",
            quote=True
        )
        LOGGER.warning(f"User {user_id} tried to merge with less than 2 videos ({len(session['videos'])}).")
        return
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ A merge is already in progress. Please wait for the current one to finish or use /cancel.",
            quote=True
        )
        LOGGER.warning(f"User {user_id} tried to start merge while one is already in progress.")
        return
    
    await start_merge_process(client, message)

async def start_merge_process(client, message: Message):
    """
    Perform download, merge, then prompt upload choice.
    This function is called by /merge command or 'merge_videos' callback.
    """
    user_id = message.from_user.id
    session = get_user_session(user_id)
    session["merge_in_progress"] = True
    
    progress_msg = await message.reply_text("🔄 Starting video merge process…", quote=True)
    LOGGER.info(f"User {user_id}: Merge process initiated.")

    try:
        # Download videos
        video_paths = []
        for i, info in enumerate(session["videos"]):
            current_video_num = i + 1
            total_videos = len(session["videos"])
            
            await progress_msg.edit_text(
                f"📥 Downloading video {current_video_num}/{total_videos}…\n"
                f"File: `{info.get('file_name', 'N/A')}`" # File name भी दिखाएं
            )
            LOGGER.info(f"User {user_id}: Downloading video {current_video_num}/{total_videos}: {info.get('file_id') or info.get('url')}")
            
            path = None
            if info.get("local_path"):
                path = info["local_path"]
            elif info.get("file_id"):
                try:
                    msg = await client.get_messages(user_id, info["message_id"])
                    if not msg or not msg.video:
                        LOGGER.error(f"User {user_id}: Message {info['message_id']} not found or not a video.")
                        await progress_msg.edit_text(f"❌ Could not retrieve video {current_video_num}. Skipping.")
                        continue
                    path = await download_from_tg(msg, user_id, progress_msg)
                except Exception as e:
                    LOGGER.error(f"User {user_id}: Failed to get or download Telegram video {info['message_id']}: {e}", exc_info=True)
                    await progress_msg.edit_text(f"❌ Failed to download Telegram video {current_video_num}. Skipping.")
                    continue
            elif info.get("url"):
                try:
                    path = await download_from_url(info["url"], user_id, progress_msg)
                except Exception as e:
                    LOGGER.error(f"User {user_id}: Failed to download video from URL {info['url']}: {e}", exc_info=True)
                    await progress_msg.edit_text(f"❌ Failed to download URL video {current_video_num}. Skipping.")
                    continue
            
            if path and os.path.exists(path):
                video_paths.append(path)
                LOGGER.info(f"User {user_id}: Successfully downloaded {os.path.basename(path)}.")
            else:
                LOGGER.warning(f"User {user_id}: Download failed or path invalid for video {current_video_num}.")

        if len(video_paths) < 2:
            await progress_msg.edit_text(
                f"❌ Download failed: only {len(video_paths)} videos were successfully downloaded. "
                "You need at least 2 videos to merge. Please try again with valid videos."
            )
            LOGGER.error(f"User {user_id}: Not enough videos ({len(video_paths)}) for merge after download.")
            return
        
        # Merge videos
        await progress_msg.edit_text(f"🎬 Merging {len(video_paths)} videos… This may take a while.")
        LOGGER.info(f"User {user_id}: Starting FFmpeg merge of {len(video_paths)} videos.")
        
        merged_path = await merge_videos(video_paths, user_id, progress_msg)
        
        if not merged_path or not os.path.exists(merged_path):
            await progress_msg.edit_text("❌ Video merge failed. Please check logs for details or try again.")
            LOGGER.error(f"User {user_id}: FFmpeg merge failed. Merged path: {merged_path}")
            return
        
        LOGGER.info(f"User {user_id}: Merge completed successfully to {merged_path}.")

        # Prompt upload choice
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload to Telegram", callback_data=f"upload:tg:{merged_path}")],
            [InlineKeyboardButton("☁️ Upload to GoFile (Large Files)", callback_data=f"upload:gofile:{merged_path}")]
        ])
        await progress_msg.edit_text(
            "✅ Merge complete!\nWhere would you like me to upload the merged video?",
            reply_markup=buttons
        )
    
    except Exception as e:
        error_message = f"❌ An unexpected error occurred during the merge process: {e}"
        await progress_msg.edit_text(error_message)
        LOGGER.critical(f"User {user_id}: Unhandled exception during merge process: {e}", exc_info=True)
    finally:
        session["merge_in_progress"] = False
        session["videos"].clear() # Clear video queue regardless of outcome
        await clean_temp_files(user_id) # Always clean up temp files
        LOGGER.info(f"User {user_id}: Merge process finished. Temporary files cleaned.")

# This handler is largely redundant if callback_handler.py handles 'upload:' queries.
# If both are active, it can lead to duplicate handling.
# It's better to keep all generic callback handling in callback_handler.py
# If you intend for this module to handle upload choices, you might remove it from callback_handler.py
# and add specific logging/cleanup here.
# For now, I will keep it as it is, assuming callback_handler.py has precedence or this is a backup.
@bot_client.on_callback_query(filters.regex(r"^upload:(tg|gofile):"))
async def on_upload_choice(client, query: CallbackQuery):
    """
    Handle post-merge upload choice.
    NOTE: This might be redundant if `callback_handler.py` also processes `upload:` callbacks.
    Consider centralizing `upload:` callback logic in `callback_handler.py`.
    """
    data = query.data
    user_id = query.from_user.id
    LOGGER.info(f"User {user_id}: Upload choice callback received: {data}")

    try:
        _, method, path = data.split(":", 2)
    except ValueError:
        await query.answer("❓ Malformed upload action!", show_alert=True)
        LOGGER.error(f"Malformed upload callback data: {data} for user {user_id}")
        return

    await query.answer("Processing upload request...", show_alert=False) # UX improvement
    
    if not os.path.exists(path):
        LOGGER.warning(f"User {user_id}: Merged file {path} not found for upload.")
        return await query.message.edit_text("❌ Merged file not found or already deleted.")
    
    success = False
    if method == "tg":
        try:
            await query.message.edit_text("📤 Uploading to Telegram… This might take a while.")
            await upload_to_telegram(
                client=client,
                chat_id=user_id,
                file_path=path,
                status_message=query.message,
                custom_filename=Config.MERGED_VIDEO_FILENAME if hasattr(Config, 'MERGED_VIDEO_FILENAME') else "merged_video"
            )
            success = True
        except Exception as e:
            LOGGER.error(f"User {user_id}: Telegram upload failed for {path}: {e}", exc_info=True)
            await query.message.edit_text(f"❌ Telegram upload failed: {e}")
    elif method == "gofile":
        try:
            await query.message.edit_text("☁️ Uploading to GoFile… This might take longer for large files.")
            link = await upload_large_file(path, query.message)
            if link:
                await query.message.edit_text(f"✅ GoFile link: {link}")
                success = True
            else:
                await query.message.edit_text("❌ GoFile upload failed. No link received.")
        except Exception as e:
            LOGGER.error(f"User {user_id}: GoFile upload failed for {path}: {e}", exc_info=True)
            await query.message.edit_text(f"❌ GoFile upload failed: {e}")
    else:
        LOGGER.warning(f"User {user_id}: Unknown upload method '{method}' requested for {path}.")
        await query.message.edit_text("❓ Unknown upload target!")
        
    # Clean up merged file after successful upload, regardless of where the handler is.
    if success and os.path.exists(path):
        try:
            os.remove(path)
            LOGGER.info(f"User {user_id}: Cleaned up merged file: {path} after upload.")
        except OSError as e:
            LOGGER.error(f"User {user_id}: Failed to delete merged file {path}: {e}")

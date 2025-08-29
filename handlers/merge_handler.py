"""
Enhanced merge handler with post-merge upload choice (Telegram or GoFile)
"""

import os
import asyncio
import time
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.client import bot_client, get_user_session
from bot.config import Config
from utils.file_utils import download_from_tg, download_from_url, clean_temp_files
from utils.ffmpeg_utils import merge_videos
from utils.upload_utils import upload_large_file, upload_to_telegram

@bot_client.on_message(filters.command("merge") & filters.private)
async def merge_command(client, message: Message):
    """Handle /merge command"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if len(session["videos"]) < 2:
        await message.reply_text(
            "❌ You need at least 2 videos to merge. Send more videos first.",
            quote=True
        )
        return
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ A merge is already in progress. Please wait.",
            quote=True
        )
        return
    
    await start_merge_process(client, message)

async def start_merge_process(client, message: Message):
    """Perform download, merge, then prompt upload choice"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    session["merge_in_progress"] = True
    
    progress_msg = await message.reply_text("🔄 Starting merge process…", quote=True)
    try:
        # Download videos
        video_paths = []
        for i, info in enumerate(session["videos"]):
            await progress_msg.edit_text(f"📥 Downloading {i+1}/{len(session['videos'])}…")
            
            if info.get("local_path"):
                path = info["local_path"]
            elif info.get("file_id"):
                msg = await client.get_messages(user_id, info["message_id"])
                path = await download_from_tg(msg, user_id, progress_msg)
            else:
                path = await download_from_url(info["url"], user_id, progress_msg)
            
            if path:
                video_paths.append(path)
        
        if len(video_paths) < 2:
            await progress_msg.edit_text(
                f"❌ Download failed: only {len(video_paths)} videos downloaded."
            )
            return
        
        # Merge videos
        merged_path = await merge_videos(video_paths, user_id, progress_msg)
        if not merged_path or not os.path.exists(merged_path):
            await progress_msg.edit_text("❌ Merge failed. Check logs.")
            return
        
        # Prompt upload choice
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Telegram", callback_data=f"upload:tg:{merged_path}")],
            [InlineKeyboardButton("☁️ GoFile",   callback_data=f"upload:gofile:{merged_path}")]
        ])
        await progress_msg.edit_text(
            "✅ Merge complete!\nWhere should I upload the merged video?",
            reply_markup=buttons
        )
    
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {e}")
        print(f"Merge error: {e}")
    finally:
        session["merge_in_progress"] = False
        session["videos"].clear()
        await clean_temp_files(user_id)

@bot_client.on_callback_query(filters.regex(r"^upload:(tg|gofile):"))
async def on_upload_choice(client, query: CallbackQuery):
    """Handle post-merge upload choice"""
    _, method, path = query.data.split(":", 2)
    await query.answer()
    
    if not os.path.exists(path):
        return await query.message.edit_text("❌ Merged file not found.")
    
    if method == "tg":
        await query.message.edit_text("📤 Uploading to Telegram…")
        # Use the util function so that size/caption/progress is consistent and thumbnail is NOT used
        await upload_to_telegram(
            client=client,
            chat_id=query.from_user.id,
            file_path=path,
            status_message=query.message,
            custom_filename="merged_video"
        )
    else:
        await query.message.edit_text("☁️ Uploading to GoFile…")
        link = await upload_large_file(path, query.message)
        if link:
            await query.message.edit_text(f"✅ GoFile link: {link}")
        else:
            await query.message.edit_text("❌ GoFile upload failed.")

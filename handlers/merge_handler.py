"""
Enhanced video merge handler with advanced features
"""

import os
import asyncio
import time
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session, merge_tasks
from bot.config import Config
from utils.helpers import format_duration, get_file_size
from utils.file_utils import download_video, clean_temp_files
from utils.ffmpeg_utils import merge_videos
from utils.upload_utils import upload_large_file, upload_to_telegram

@bot_client.on_message(filters.command("merge") & filters.private)
async def merge_command(client, message: Message):
    """Handle /merge command"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if len(session["videos"]) < 2:
        await message.reply_text(
            "❌ **Insufficient Videos**\n\n"
            "You need at least 2 videos to merge. Please send more videos first.",
            quote=True
        )
        return
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ **Merge Already in Progress**\n\n"
            "Please wait for the current operation to complete.",
            quote=True
        )
        return
    
    # Start merge process
    await start_merge_process(client, message, user_id)

async def start_merge_process(client, message: Message, user_id: int):
    """Enhanced merge process with advanced features"""
    session = get_user_session(user_id)
    session["merge_in_progress"] = True
    
    # Create progress message
    progress_msg = await message.reply_text(
        "🔄 **Starting Video Merge Process...**\n\n"
        "⏳ Please wait while I process your videos.",
        quote=True
    )
    
    try:
        # Store merge task
        merge_tasks[user_id] = {
            "progress_msg": progress_msg,
            "start_time": time.time()
        }
        
        # Download all videos
        await progress_msg.edit_text(
            "📥 **Downloading Videos...**\n\n"
            f"Processing {len(session['videos'])} videos..."
        )
        
        video_paths = []
        for i, video_info in enumerate(session["videos"]):
            await progress_msg.edit_text(
                f"📥 **Downloading Videos... ({i+1}/{len(session['videos'])})**\n\n"
                f"Current: {video_info['file_name']}"
            )
            
            # Check if it's already downloaded (URL videos)
            if video_info.get("local_path") and os.path.exists(video_info["local_path"]):
                video_paths.append(video_info["local_path"])
            elif video_info.get("file_id"):
                # Download from Telegram
                path = await download_video(
                    client, 
                    video_info["file_id"], 
                    video_info["file_name"], 
                    user_id, 
                    progress_msg
                )
                if path:
                    video_paths.append(path)
        
        if not video_paths or len(video_paths) < 2:
            await progress_msg.edit_text("❌ **Download Failed**\n\nFailed to download videos.")
            return
        
        # Create user-specific output directory
        user_merged_dir = os.path.join(Config.MERGED_DIR, str(user_id))
        os.makedirs(user_merged_dir, exist_ok=True)
        
        # Merge videos
        output_path = os.path.join(user_merged_dir, f"merged_{int(time.time())}.mkv")
        thumbnail_path = session.get("thumbnail")
        
        success = await merge_videos(video_paths, output_path, thumbnail_path, progress_msg)
        
        if not success or not os.path.exists(output_path):
            await progress_msg.edit_text("❌ **Merge Failed**\n\nFailed to merge videos.")
            return
        
        # Upload merged video
        file_size = os.path.getsize(output_path)
        
        if file_size > Config.LARGE_FILE_THRESHOLD:
            # Upload to cloud
            await progress_msg.edit_text("☁️ **File is large, uploading to cloud...**")
            
            download_link = await upload_large_file(output_path, progress_msg)
            
            if download_link:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("☁️ Download from Cloud", url=download_link)]
                ])
                
                await progress_msg.edit_text(
                    "✅ **Merge Completed Successfully!**\n\n"
                    f"📁 **File Size:** {get_file_size(file_size)}\n"
                    f"⏱ **Processing Time:** {format_duration(int(time.time() - merge_tasks[user_id]['start_time']))}\n\n"
                    "⬇️ **Download your merged video from the cloud:**",
                    reply_markup=keyboard
                )
            else:
                await progress_msg.edit_text("❌ **Upload Failed**\n\nFailed to upload to cloud storage.")
        else:
            # Upload to Telegram
            custom_filename = f"merged_video_{int(time.time())}"
            
            success = await upload_to_telegram(
                client, 
                user_id, 
                output_path, 
                progress_msg, 
                thumbnail_path, 
                custom_filename
            )
            
            if not success:
                # Fallback to cloud upload
                download_link = await upload_large_file(output_path, progress_msg)
                if download_link:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("☁️ Download from Cloud", url=download_link)]
                    ])
                    
                    await progress_msg.edit_text(
                        "✅ **Merge Completed!** (Uploaded to cloud as fallback)\n\n"
                        f"📁 **File Size:** {get_file_size(file_size)}\n"
                        "⬇️ **Download your merged video:**",
                        reply_markup=keyboard
                    )
    
    except Exception as e:
        await progress_msg.edit_text(f"❌ **Error Occurred**\n\n`{str(e)}`")
        print(f"Merge process error: {e}")
    
    finally:
        # Clean up
        session["merge_in_progress"] = False
        session["videos"].clear()
        
        if user_id in merge_tasks:
            del merge_tasks[user_id]
        
        # Clean temporary files
        await clean_temp_files(user_id)

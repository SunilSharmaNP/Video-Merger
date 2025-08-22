"""
Video merge handler
"""

import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.client import bot_client, get_user_session, merge_tasks
from utils.ffmpeg_utils import merge_videos
from utils.file_utils import download_video, clean_temp_files
from utils.upload_utils import upload_large_file
from utils.helpers import format_duration, get_file_size

@bot_client.on_message(filters.video & filters.private)
async def handle_video_upload(client: Client, message: Message):
    """Handle video file uploads"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ **Merge in Progress**\n\n"
            "Please wait for the current merge operation to complete.",
            quote=True
        )
        return
    
    # Check file size
    file_size = message.video.file_size
    if file_size > Config.MAX_FILE_SIZE:
        await message.reply_text(
            f"❌ **File Too Large**\n\n"
            f"Maximum file size allowed: {Config.MAX_FILE_SIZE // 1024 // 1024}MB\n"
            f"Your file size: {file_size // 1024 // 1024}MB",
            quote=True
        )
        return
    
    # Add video to session
    video_info = {
        "file_id": message.video.file_id,
        "file_name": getattr(message.video, 'file_name', f"video_{len(session['videos']) + 1}.mp4"),
        "duration": message.video.duration,
        "file_size": file_size,
        "message_id": message.id
    }
    
    session["videos"].append(video_info)
    
    # Create progress message
    video_count = len(session["videos"])
    total_size = sum(v["file_size"] for v in session["videos"])
    total_duration = sum(v["duration"] for v in session["videos"])
    
    keyboard = None
    if video_count >= 2:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Merge Videos", callback_data="merge_videos"),
                InlineKeyboardButton("🗑 Clear All", callback_data="clear_videos")
            ]
        ])
    
    progress_text = (
        f"📥 **Video Added Successfully!**\n\n"
        f"📊 **Current Status:**\n"
        f"• Videos in queue: **{video_count}**\n"
        f"• Total size: **{get_file_size(total_size)}**\n"
        f"• Total duration: **{format_duration(total_duration)}**\n\n"
    )
    
    if video_count == 1:
        progress_text += "📨 **Send more videos** to merge them together!"
    else:
        progress_text += "✅ **Ready to merge!** Click the merge button below."
    
    await message.reply_text(
        progress_text,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("merge") & filters.private)
async def merge_command(client: Client, message: Message):
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

async def start_merge_process(client: Client, message: Message, user_id: int):
    """Start the video merge process"""
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
            
            path = await download_video(client, video_info["file_id"], video_info["file_name"])
            if path:
                video_paths.append(path)
        
        if not video_paths or len(video_paths) < 2:
            await progress_msg.edit_text("❌ **Download Failed**\n\nFailed to download videos.")
            return
        
        # Merge videos
        await progress_msg.edit_text(
            "🎬 **Merging Videos...**\n\n"
            "This may take a few minutes depending on video size and duration."
        )
        
        output_path = os.path.join(Config.MERGED_DIR, f"merged_{user_id}_{int(time.time())}.mp4")
        thumbnail_path = session.get("thumbnail")
        
        success = await merge_videos(video_paths, output_path, thumbnail_path, progress_msg)
        
        if not success or not os.path.exists(output_path):
            await progress_msg.edit_text("❌ **Merge Failed**\n\nFailed to merge videos.")
            return
        
        # Upload merged video
        file_size = os.path.getsize(output_path)
        
        if file_size > Config.LARGE_FILE_THRESHOLD:
            # Upload to cloud
            await progress_msg.edit_text("☁️ **Uploading to Cloud...**\n\nFile is large, uploading to cloud storage.")
            download_link = await upload_large_file(output_path)
            
            if download_link:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("☁️ Download from Cloud", url=download_link)]
                ])
                
                await progress_msg.edit_text(
                    "✅ **Merge Completed Successfully!**\n\n"
                    f"📁 **File Size:** {get_file_size(file_size)}\n"
                    f"⏱ **Processing Time:** {format_duration(int(time.time() - merge_tasks[user_id]['start_time']))}\n\n"
                    "⬇️ **Download your merged video from the cloud link below:**",
                    reply_markup=keyboard
                )
            else:
                await progress_msg.edit_text("❌ **Upload Failed**\n\nFailed to upload to cloud storage.")
        else:
            # Upload to Telegram
            await progress_msg.edit_text("📤 **Uploading Merged Video...**")
            
            # Send the merged video
            with open(output_path, 'rb') as video_file:
                await client.send_video(
                    chat_id=user_id,
                    video=video_file,
                    caption=(
                        "✅ **Video Merge Completed!**\n\n"
                        f"📁 **Size:** {get_file_size(file_size)}\n"
                        f"⏱ **Processing Time:** {format_duration(int(time.time() - merge_tasks[user_id]['start_time']))}\n\n"
                        "🤖 **Merged by:** Video Merge Bot"
                    ),
                    thumb=thumbnail_path,
                    progress=upload_progress,
                    progress_args=(progress_msg,)
                )
            
            await progress_msg.delete()
    
    except Exception as e:
        await progress_msg.edit_text(f"❌ **Error Occurred**\n\n`{str(e)}`")
    
    finally:
        # Clean up
        session["merge_in_progress"] = False
        session["videos"].clear()
        
        if user_id in merge_tasks:
            del merge_tasks[user_id]
        
        # Clean temporary files
        await clean_temp_files(user_id)

async def upload_progress(current, total, progress_msg):
    """Upload progress callback"""
    try:
        percent = (current / total) * 100
        await progress_msg.edit_text(
            f"📤 **Uploading Merged Video...**\n\n"
            f"Progress: {percent:.1f}% ({get_file_size(current)}/{get_file_size(total)})"
        )
    except:
        pass

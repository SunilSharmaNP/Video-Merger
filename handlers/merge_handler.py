"""
Enhanced merge handler with proper download logic
"""

import os
import asyncio
import time
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session, merge_tasks
from bot.config import Config
from utils.helpers import format_duration, get_file_size
from utils.file_utils import download_from_tg, clean_temp_files
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
    """Enhanced merge process with detailed debugging"""
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
        
        print(f"Starting merge for user {user_id}")
        print(f"Videos in session: {len(session['videos'])}")
        
        # Download all videos
        await progress_msg.edit_text(
            "📥 **Downloading Videos...**\n\n"
            f"Processing {len(session['videos'])} videos..."
        )
        
        video_paths = []
        for i, video_info in enumerate(session["videos"]):
            await progress_msg.edit_text(
                f"📥 **Downloading Videos... ({i+1}/{len(session['videos'])})**\n\n"
                f"Current: {video_info['file_name']}\n"
                f"Source: {video_info.get('source', 'unknown')}"
            )
            
            print(f"Processing video {i+1}: {video_info}")
            
            try:
                # Check if it's already downloaded (URL videos)
                if video_info.get("local_path") and os.path.exists(video_info["local_path"]):
                    video_paths.append(video_info["local_path"])
                    print(f"Using existing file: {video_info['local_path']}")
                    
                elif video_info.get("file_id"):
                    # Download from Telegram using message
                    original_msg = None
                    try:
                        original_msg = await client.get_messages(user_id, video_info["message_id"])
                        print(f"Got original message for {video_info['file_name']}")
                    except Exception as e:
                        print(f"Failed to get original message: {e}")
                    
                    if original_msg and (original_msg.video or original_msg.document):
                        path = await download_from_tg(original_msg, user_id, progress_msg)
                        if path and os.path.exists(path):
                            video_paths.append(path)
                            print(f"Downloaded from Telegram: {path}")
                        else:
                            print(f"Failed to download from Telegram: {video_info['file_name']}")
                    else:
                        print(f"Invalid original message for: {video_info['file_name']}")
                        
                else:
                    print(f"No download method for: {video_info['file_name']}")
                    
            except Exception as e:
                print(f"Download error for {video_info['file_name']}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"Total video paths collected: {len(video_paths)}")
        print(f"Video paths: {video_paths}")
        
        if not video_paths or len(video_paths) < 2:
            await progress_msg.edit_text(
                f"❌ **Download Failed**\n\n"
                f"Only {len(video_paths)} out of {len(session['videos'])} videos downloaded successfully.\n"
                f"Need at least 2 videos to merge.\n\n"
                f"**Debug Info:**\n"
                f"• Session videos: {len(session['videos'])}\n"
                f"• Downloaded paths: {len(video_paths)}\n"
                f"• Check logs for detailed error messages"
            )
            return
        
        # Verify all files exist and are valid
        valid_paths = []
        for path in video_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                valid_paths.append(path)
                print(f"Valid file: {path} ({os.path.getsize(path)} bytes)")
            else:
                print(f"Invalid/missing file: {path}")
        
        if len(valid_paths) < 2:
            await progress_msg.edit_text(
                f"❌ **File Validation Failed**\n\n"
                f"Only {len(valid_paths)} valid files found. Need at least 2 videos to merge.\n\n"
                f"**File Status:**\n" +
                "\n".join([f"• {os.path.basename(p)}: {'✅' if os.path.exists(p) else '❌'}" for p in video_paths])
            )
            return
        
        # Merge videos using enhanced function
        output_path = await merge_videos(valid_paths, user_id, progress_msg)
        
        if not output_path or not os.path.exists(output_path):
            await progress_msg.edit_text("❌ **Merge Failed**\n\nFailed to merge videos. Check logs for details.")
            return
        
        # Upload merged video
        file_size = os.path.getsize(output_path)
        print(f"Merged file size: {file_size} bytes")
        
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
            thumbnail_path = session.get("thumbnail")
            
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
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        session["merge_in_progress"] = False
        session["videos"].clear()
        
        if user_id in merge_tasks:
            del merge_tasks[user_id]
        
        # Clean temporary files
        await clean_temp_files(user_id)

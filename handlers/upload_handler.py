"""
Upload handler for videos and thumbnails
"""

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session
from bot.config import Config
from utils.helpers import get_file_size, format_duration

@bot_client.on_message(filters.video & filters.private)
async def handle_video_upload(client, message: Message):
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
        "duration": message.video.duration or 0,
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
    
    progress_text = f"""
📥 **Video Added Successfully!**

📊 **Current Status:**
• Videos in queue: **{video_count}**
• Total size: **{get_file_size(total_size)}**
• Total duration: **{format_duration(total_duration)}**

"""
    
    if video_count == 1:
        progress_text += "📨 **Send more videos** to merge them together!"
    else:
        progress_text += "✅ **Ready to merge!** Click the merge button below."
    
    await message.reply_text(
        progress_text,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.document & filters.private)
async def handle_document_upload(client, message: Message):
    """Handle document uploads (video files)"""
    user_id = message.from_user.id
    document = message.document
    
    # Check if it's a video file
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp']
    
    if document.file_name and any(document.file_name.lower().endswith(ext) for ext in video_extensions):
        session = get_user_session(user_id)
        
        if session["merge_in_progress"]:
            await message.reply_text(
                "⏳ **Merge in Progress**\n\n"
                "Please wait for the current merge operation to complete.",
                quote=True
            )
            return
        
        # Check file size
        file_size = document.file_size
        if file_size > Config.MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ **File Too Large**\n\n"
                f"Maximum file size allowed: {Config.MAX_FILE_SIZE // 1024 // 1024}MB\n"
                f"Your file size: {file_size // 1024 // 1024}MB",
                quote=True
            )
            return
        
        # Add to video queue
        video_info = {
            "file_id": document.file_id,
            "file_name": document.file_name,
            "duration": 0,  # Duration not available for documents
            "file_size": file_size,
            "message_id": message.id
        }
        
        session["videos"].append(video_info)
        
        video_count = len(session["videos"])
        keyboard = None
        if video_count >= 2:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 Merge Videos", callback_data="merge_videos"),
                    InlineKeyboardButton("🗑 Clear All", callback_data="clear_videos")
                ]
            ])
        
        await message.reply_text(
            f"📁 **Video Document Added!**\n\n"
            f"**File:** {document.file_name}\n"
            f"**Size:** {file_size // 1024 // 1024}MB\n\n"
            f"**Videos in queue:** {video_count}\n\n"
            f"{'✅ Ready to merge! Click the button below.' if video_count >= 2 else '📨 Send more videos to merge them together.'}",
            reply_markup=keyboard,
            quote=True
        )
    else:
        await message.reply_text(
            "📄 **Document Received**\n\n"
            "I can only process video files for merging. "
            "Please send video files (.mp4, .avi, .mov, etc.)",
            quote=True
        )

@bot_client.on_message(filters.photo & filters.private)
async def handle_photo_upload(client, message: Message):
    """Handle photo uploads (for thumbnails)"""
    user_id = message.from_user.id
    
    # Check if user is setting thumbnail
    if message.caption and "thumbnail" in message.caption.lower():
        await set_custom_thumbnail(client, message, user_id)
        return
    
    # Regular photo upload message
    await message.reply_text(
        "📸 **Photo Received!**\n\n"
        "If you want to set this as a custom thumbnail for your merged videos, "
        "use the `/set_thumbnail` command after sending this photo.",
        quote=True
    )

@bot_client.on_message(filters.command("set_thumbnail") & filters.private)
async def set_thumbnail_command(client, message: Message):
    """Handle /set_thumbnail command"""
    user_id = message.from_user.id
    
    # Check if replying to a photo
    if message.reply_to_message and message.reply_to_message.photo:
        await set_custom_thumbnail(client, message.reply_to_message, user_id)
    else:
        await message.reply_text(
            "📸 **Set Custom Thumbnail**\n\n"
            "Please reply to a photo with this command to set it as your custom thumbnail.\n\n"
            "**Note:** This thumbnail will be used for all your merged videos until you change or delete it.",
            quote=True
        )

@bot_client.on_message(filters.command("del_thumbnail") & filters.private)
async def delete_thumbnail_command(client, message: Message):
    """Handle /del_thumbnail command"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if session.get("thumbnail"):
        # Remove thumbnail file
        import os
        if os.path.exists(session["thumbnail"]):
            os.remove(session["thumbnail"])
        
        session["thumbnail"] = None
        
        await message.reply_text(
            "🗑 **Thumbnail Deleted Successfully!**\n\n"
            "Your custom thumbnail has been removed. Default thumbnails will be used for merged videos.",
            quote=True
        )
    else:
        await message.reply_text(
            "❌ **No Custom Thumbnail Set**\n\n"
            "You don't have any custom thumbnail set. Use `/set_thumbnail` to set one.",
            quote=True
        )

async def set_custom_thumbnail(client, message: Message, user_id: int):
    """Set custom thumbnail for user"""
    try:
        from utils.file_utils import save_thumbnail
        
        # Download and save thumbnail
        thumbnail_path = await save_thumbnail(client, message.photo.file_id, user_id)
        
        if thumbnail_path:
            session = get_user_session(user_id)
            session["thumbnail"] = thumbnail_path
            
            await message.reply_text(
                "✅ **Custom Thumbnail Set Successfully!**\n\n"
                "This thumbnail will be used for all your merged videos. "
                "Use `/del_thumbnail` to remove it anytime.",
                quote=True
            )
        else:
            await message.reply_text(
                "❌ **Failed to Set Thumbnail**\n\n"
                "There was an error processing your thumbnail. Please try again.",
                quote=True
            )
    
    except Exception as e:
        await message.reply_text(
            f"❌ **Error Setting Thumbnail**\n\n`{str(e)}`",
            quote=True
        )

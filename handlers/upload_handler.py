"""
Enhanced upload handler with proper URL detection and file handling
"""

import re
import os
import logging # Logging इम्पोर्ट करें
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session
from bot.config import Config
from utils.helpers import get_file_size, format_duration
from utils.file_utils import download_from_url
# from utils.ffmpeg_utils import get_video_duration # यदि आप डॉक्यूमेंट से ड्यूरेशन निकालना चाहते हैं तो यह इम्पोर्ट करें

LOGGER = logging.getLogger(__name__) # Logger इनिशियलाइज़ करें

# Enhanced URL regex pattern
# Improved to better handle common URL structures and avoid matching plain text
URL_PATTERN = re.compile(
    r'https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
)

async def check_file_size_and_reply(message: Message, file_size: int) -> bool:
    """Checks if file size exceeds allowed limit and replies if it does."""
    if file_size > Config.MAX_FILE_SIZE:
        await message.reply_text(
            f"❌ **File Too Large**\n\n"
            f"Maximum file size allowed: `{Config.MAX_FILE_SIZE // (1024 * 1024)}MB`\n"
            f"Your file size: `{file_size // (1024 * 1024)}MB`",
            quote=True
        )
        LOGGER.warning(f"User {message.from_user.id}: File too large ({file_size} bytes). Max: {Config.MAX_FILE_SIZE}.")
        return False
    return True

async def send_queue_status_message(message: Message, session: dict, is_new_video: bool = True):
    """Sends or updates the message with current queue status."""
    user_id = message.from_user.id
    video_count = len(session["videos"])
    total_size = sum(v["file_size"] for v in session["videos"])
    total_duration = sum(v["duration"] for v in session["videos"]) # Duration केवल video messages के लिए उपलब्ध होगी

    keyboard = None
    if video_count >= 2:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Merge Videos", callback_data="merge_videos"),
                InlineKeyboardButton("🗑 Clear All", callback_data="clear_videos")
            ]
        ])

    status_text = f"""
📥 **Video Added Successfully!** (from {'URL' if session['videos'][-1].get('source') == 'url' else 'Telegram'})

📊 **Current Status:**
• Videos in queue: **`{video_count}`**
• Total size: **`{get_file_size(total_size)}`**
"""
    if total_duration > 0: # केवल तभी दिखाएं जब ड्यूरेशन उपलब्ध हो
        status_text += f"\n• Total duration: **`{format_duration(total_duration)}`**"
    
    status_text += "\n\n"
    if video_count == 1:
        status_text += "📨 **Send more videos** to merge them together!"
    else:
        status_text += "✅ **Ready to merge!** Click the merge button below."
    
    # यदि यह एक नया वीडियो है, तो एक नया संदेश भेजें; अन्यथा, मौजूदा को अपडेट करें।
    # यह URL हैंडलर के लिए अधिक उपयुक्त हो सकता है जो एक प्रगति संदेश को बनाए रखता है।
    if is_new_video:
        await message.reply_text(
            status_text,
            reply_markup=keyboard,
            quote=True
        )
    else: # URL हैंडलर के लिए, यह एक मौजूदा status_msg को एडिट कर सकता है।
        pass # इस फ़ंक्शन में status_msg ऑब्जेक्ट तक सीधी पहुँच नहीं है, इसे अलग से हैंडल किया जाएगा।


@bot_client.on_message(filters.text & filters.private & ~filters.command(["start", "help", "ping", "cancel", "merge", "set_thumbnail", "del_thumbnail", "id", "broadcast", "stats"]))
async def handle_url_message(client, message: Message):
    """Handle text messages for video URLs or general interaction."""
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    text = message.text.strip()
    urls = URL_PATTERN.findall(text)
    
    LOGGER.info(f"User {user_id} ({user_first_name}) sent text: {text}. URLs found: {len(urls)}")
    
    if not urls:
        # Regular text message - provide helpful response
        await message.reply_text(
            f"📢 You said: **`{text}`**\n\n" # Monospace for user's text
            "💡 **Tips:**\n"
            "• Send video files to merge them\n" 
            "• Send **direct video URLs** (e.g., `https://example.com/video.mp4`) to download and merge\n"
            "• Use `/ping` to test the bot\n"
            "• Use `/help` for more information",
            quote=True
        )
        return
    
    session = get_user_session(user_id)
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ **Merge in Progress**\n\n"
            "Please wait for the current merge operation to complete or use `/cancel`.",
            quote=True
        )
        LOGGER.warning(f"User {user_id} tried to add URL while merge is in progress.")
        return
    
    status_msg = await message.reply_text("📥 **Processing URLs...**", quote=True)
    
    downloaded_videos_count = 0
    total_urls = len(urls)
    
    for i, url in enumerate(urls):
        try:
            await status_msg.edit_text(
                f"📥 **Processing URLs... ({i+1}/{total_urls})**\n\n"
                f"Attempting to download: `{url}`"
            )
            LOGGER.info(f"User {user_id}: Attempting to download from URL: {url}")
            
            file_path = await download_from_url(url, user_id, status_msg)
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)
                
                # Check file size (re-check for URL downloads after actual download)
                if not await check_file_size_and_reply(status_msg, file_size):
                    LOGGER.warning(f"User {user_id}: Downloaded URL file ({file_name}) exceeds max size. Deleting temp file.")
                    os.remove(file_path) # Delete the oversized file
                    continue 

                video_info = {
                    "file_id": None,
                    "file_name": file_name,
                    "duration": 0, # Duration extraction for URL videos might require FFprobe, consider later
                    "file_size": file_size,
                    "message_id": message.id, # The message that contained the URL
                    "local_path": file_path,
                    "source": "url"
                }
                
                session["videos"].append(video_info)
                downloaded_videos_count += 1
                LOGGER.info(f"User {user_id}: Successfully added URL video: {file_name} from {url}. Path: {file_path}")
            else:
                LOGGER.warning(f"User {user_id}: Failed to download URL: {url}. File path: {file_path}")
                await status_msg.edit_text(f"❌ Failed to download from: `{url}`. Trying next URL if any.", parse_mode=ParseMode.MARKDOWN) # ParseMode specify
                await asyncio.sleep(2) # Small delay for user to read
        
        except Exception as e:
            LOGGER.error(f"User {user_id}: URL download error for {url}: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ An error occurred downloading from `{url}`: {e}", parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(2) # Small delay for user to read
            
    if downloaded_videos_count > 0:
        video_count = len(session["videos"])
        total_size = sum(v["file_size"] for v in session["videos"])
        
        keyboard = None
        if video_count >= 2:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 Merge Videos", callback_data="merge_videos"),
                    InlineKeyboardButton("🗑 Clear All", callback_data="clear_videos")
                ]
            ])
        
        progress_text = f"""
📥 **URL Download Complete!**

📊 **Current Status:**
• Downloaded from URLs: **`{downloaded_videos_count}`**
• Total videos in queue: **`{video_count}`**
• Total size: **`{get_file_size(total_size)}`**

"""
        
        if video_count == 1:
            progress_text += "📨 **Send more videos** to merge them together!"
        else:
            progress_text += "✅ **Ready to merge!** Click the merge button below."
        
        await status_msg.edit_text(progress_text, reply_markup=keyboard)
    else:
        await status_msg.edit_text(
            f"❌ **No videos downloaded**\n\n"
            f"Failed to download from `{total_urls}` URLs. Please check:\n"
            f"• URLs are direct links to video files (e.g., `.mp4`, `.mkv`)\n"
            f"• URLs are valid and accessible\n"
            f"• Bot has internet connection and access to the URLs"
        )
        LOGGER.warning(f"User {user_id}: No videos downloaded from {total_urls} URLs.")

@bot_client.on_message(filters.video & filters.private)
async def handle_video_upload(client, message: Message):
    """Handle video file uploads from Telegram."""
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    LOGGER.info(f"User {user_id} ({user_first_name}) uploaded a video: {message.video.file_name}")

    session = get_user_session(user_id)
    
    if session["merge_in_progress"]:
        await message.reply_text(
            "⏳ **Merge in Progress**\n\n"
            "Please wait for the current merge operation to complete or use `/cancel`.",
            quote=True
        )
        LOGGER.warning(f"User {user_id} tried to add video while merge is in progress.")
        return
    
    file_size = message.video.file_size
    if not await check_file_size_and_reply(message, file_size):
        return
    
    video_info = {
        "file_id": message.video.file_id,
        "file_name": getattr(message.video, 'file_name', f"video_{len(session['videos']) + 1}.mp4"),
        "duration": message.video.duration or 0,
        "file_size": file_size,
        "message_id": message.id,
        "local_path": None, # Downloaded during merge process
        "source": "telegram"
    }
    
    session["videos"].append(video_info)
    LOGGER.info(f"User {user_id}: Added Telegram video {video_info['file_name']} (file_id: {message.video.file_id}). Videos in queue: {len(session['videos'])}")
    
    await send_queue_status_message(message, session, is_new_video=True)


@bot_client.on_message(filters.document & filters.private)
async def handle_document_upload(client, message: Message):
    """Handle document uploads, specifically checking for video files."""
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    document = message.document
    
    # Check if it's a video file based on MIME type or extension
    # MIME type is more reliable than extension for documents
    is_video_mime = document.mime_type and document.mime_type.startswith('video/')
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.webm']
    is_video_extension = document.file_name and any(document.file_name.lower().endswith(ext) for ext in video_extensions)

    if is_video_mime or is_video_extension:
        LOGGER.info(f"User {user_id} ({user_first_name}) uploaded a document (likely video): {document.file_name}")
        session = get_user_session(user_id)
        
        if session["merge_in_progress"]:
            await message.reply_text(
                "⏳ **Merge in Progress**\n\n"
                "Please wait for the current merge operation to complete or use `/cancel`.",
                quote=True
            )
            LOGGER.warning(f"User {user_id} tried to add document video while merge is in progress.")
            return
        
        file_size = document.file_size
        if not await check_file_size_and_reply(message, file_size):
            return
        
        video_info = {
            "file_id": document.file_id,
            "file_name": document.file_name,
            "duration": 0,  # Duration not directly available for documents from Telegram API
            "file_size": file_size,
            "message_id": message.id,
            "local_path": None,
            "source": "document"
        }
        
        session["videos"].append(video_info)
        LOGGER.info(f"User {user_id}: Added document video {video_info['file_name']} (file_id: {document.file_id}). Videos in queue: {len(session['videos'])}")
        
        # Similar status message as handle_video_upload
        video_count = len(session["videos"])
        total_size = sum(v["file_size"] for v in session["videos"])
        
        keyboard = None
        if video_count >= 2:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 Merge Videos", callback_data="merge_videos"),
                    InlineKeyboardButton("🗑 Clear All", callback_data="clear_videos")
                ]
            ])
        
        progress_text = f"""
📁 **Video Document Added!**

📊 **Current Status:**
• Videos in queue: **`{video_count}`**
• Total size: **`{get_file_size(total_size)}`**
"""
        # Duration for document videos is not easily available, so skip
        
        progress_text += "\n\n"
        if video_count == 1:
            progress_text += "📨 **Send more videos** to merge them together!"
        else:
            progress_text += "✅ **Ready to merge!** Click the merge button below."
        
        await message.reply_text(
            progress_text,
            reply_markup=keyboard,
            quote=True
        )
    else:
        LOGGER.info(f"User {user_id}: Received non-video document: {document.file_name} (MIME: {document.mime_type})")
        await message.reply_text(
            "📄 **Document Received**\n\n"
            "I can only process video files for merging. "
            "Please send video files (.mp4, .avi, .mov, etc.) or video URLs.",
            quote=True
        )

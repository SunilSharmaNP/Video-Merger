"""
Advanced file utility functions with FloodWait prevention
"""

import os
import time
import aiofiles
import aiohttp
from bot.config import Config
from utils.helpers import sanitize_filename, get_file_size, get_progress_bar

# Global dictionary for throttling message edits
last_edit_time = {}
EDIT_THROTTLE_SECONDS = 4.0

async def smart_progress_editor(status_message, text: str):
    """Throttled editor to prevent FloodWait errors during progress updates"""
    if not status_message or not hasattr(status_message, 'chat'):
        return
    
    message_key = f"{status_message.chat.id}_{status_message.id}"
    now = time.time()
    last_time = last_edit_time.get(message_key, 0)
    
    if (now - last_time) > EDIT_THROTTLE_SECONDS:
        try:
            await status_message.edit_text(text)
            last_edit_time[message_key] = now
        except Exception:
            pass

async def download_video(client, file_id: str, file_name: str, user_id: int = None, status_message=None) -> str:
    """Download video from Telegram with progress tracking"""
    try:
        # Create user-specific directory
        if user_id:
            download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
            os.makedirs(download_dir, exist_ok=True)
        else:
            download_dir = Config.DOWNLOAD_DIR
        
        safe_filename = sanitize_filename(file_name)
        download_path = os.path.join(download_dir, safe_filename)
        
        # Progress callback function
        async def progress_func(current, total):
            if status_message:
                progress = current / total
                progress_text = (
                    f"📥 **Downloading from Telegram...**\n"
                    f"➢ `{safe_filename}`\n"
                    f"➢ {get_progress_bar(progress)} `{progress:.1%}`\n"
                    f"➢ **Size:** `{get_file_size(current)}` / `{get_file_size(total)}`"
                )
                await smart_progress_editor(status_message, progress_text)
        
        # Download file
        file_path = await client.download_media(
            file_id, 
            file_name=download_path,
            progress=progress_func if status_message else None
        )
        
        if status_message:
            await status_message.edit_text(f"✅ **Downloaded:** `{safe_filename}`\n\nPreparing to merge...")
        
        return file_path if os.path.exists(file_path) else None
    
    except Exception as e:
        if status_message:
            try:
                await status_message.edit_text(f"❌ **Download Failed!**\nError: `{str(e)}`")
            except:
                pass
        print(f"Download error: {e}")
        return None

async def download_from_url(url: str, user_id: int, status_message=None) -> str:
    """Download file from direct URL with progress tracking"""
    try:
        file_name = url.split('/')[-1] or f"video_{int(time.time())}.mp4"
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        os.makedirs(user_download_dir, exist_ok=True)
        dest_path = os.path.join(user_download_dir, file_name)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(dest_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0 and status_message:
                                progress = downloaded / total_size
                                progress_text = (
                                    f"📥 **Downloading from URL...**\n"
                                    f"➢ `{file_name}`\n"
                                    f"➢ {get_progress_bar(progress)} `{progress:.1%}`\n"
                                    f"➢ **Size:** `{get_file_size(downloaded)}` / `{get_file_size(total_size)}`"
                                )
                                await smart_progress_editor(status_message, progress_text)
                    
                    if status_message:
                        await status_message.edit_text(f"✅ **Downloaded:** `{file_name}`\n\nPreparing to merge...")
                    
                    return dest_path
                else:
                    if status_message:
                        await status_message.edit_text(f"❌ **Download Failed!**\nStatus: {resp.status} for URL: `{url}`")
                    return None
    
    except Exception as e:
        if status_message:
            try:
                await status_message.edit_text(f"❌ **Download Failed!**\nError: `{str(e)}`")
            except:
                pass
        return None

async def save_thumbnail(client, file_id: str, user_id: int) -> str:
    """Download and save thumbnail"""
    try:
        thumbnail_path = os.path.join(Config.THUMBNAILS_DIR, f"thumb_{user_id}.jpg")
        await client.download_media(file_id, thumbnail_path)
        
        if os.path.exists(thumbnail_path):
            return thumbnail_path
        return None
    
    except Exception as e:
        print(f"Thumbnail save error: {e}")
        return None

async def create_default_thumbnail(video_path: str) -> str:
    """Create default thumbnail from video"""
    try:
        from utils.ffmpeg_utils import get_video_info
        
        thumbnail_path = f"{os.path.splitext(video_path)[0]}.jpg"
        metadata = await get_video_info(video_path)
        
        if not metadata or not metadata.get("format", {}).get("duration"):
            print(f"Could not get duration for '{video_path}'. Skipping default thumbnail.")
            return None
        
        duration = float(metadata["format"]["duration"])
        thumbnail_time = duration / 2
        
        import asyncio
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', video_path,
            '-ss', str(thumbnail_time), '-vframes', '1',
            '-c:v', 'mjpeg', '-f', 'image2', '-y', thumbnail_path
        ]
        
        process = await asyncio.create_subprocess_exec(*command, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"Error creating default thumbnail for '{video_path}': {stderr.decode().strip()}")
            return None
        
        return thumbnail_path if os.path.exists(thumbnail_path) else None
    
    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return None

async def clean_temp_files(user_id: int):
    """Clean temporary files for user"""
    try:
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        
        # Clean download directory
        if os.path.exists(user_download_dir):
            for file in os.listdir(user_download_dir):
                try:
                    os.remove(os.path.join(user_download_dir, file))
                except:
                    pass
        
        # Clean merged directory (old files)
        for file in os.listdir(Config.MERGED_DIR):
            if f"merged_{user_id}" in file:
                try:
                    file_path = os.path.join(Config.MERGED_DIR, file)
                    # Remove files older than 1 hour
                    if os.path.getctime(file_path) < (time.time() - 3600):
                        os.remove(file_path)
                except:
                    pass
    
    except Exception as e:
        print(f"Cleanup error: {e}")

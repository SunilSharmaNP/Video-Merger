"""
Bulletproof file utilities with comprehensive error handling
"""

import os
import time
import aiofiles
import aiohttp
from bot.config import Config
from utils.helpers import sanitize_filename, get_file_size, get_progress_bar
import uuid

# Global throttling for FloodWait prevention
last_edit_time = {}
EDIT_THROTTLE_SECONDS = 4.0

async def smart_progress_editor(status_message, text: str):
    """Throttled editor to prevent FloodWait errors"""
    if not status_message or not hasattr(status_message, 'chat'):
        return
    
    try:
        message_key = f"{status_message.chat.id}_{status_message.id}"
        now = time.time()
        last_time = last_edit_time.get(message_key, 0)
        
        if (now - last_time) > EDIT_THROTTLE_SECONDS:
            await status_message.edit_text(text)
            last_edit_time[message_key] = now
    except Exception as e:
        print(f"Progress editor error: {e}")

def safe_filename_from_url(url: str) -> str:
    """Safely extract filename from URL with fallback"""
    try:
        if not url or not isinstance(url, str):
            return f"video_{int(time.time())}.mp4"
        
        # Extract filename from URL
        url_parts = url.rstrip('/').split('/')
        filename = url_parts[-1] if url_parts else f"video_{int(time.time())}.mp4"
        
        # Remove query parameters
        if '?' in filename:
            filename = filename.split('?')[0]
        
        # Ensure it has an extension
        if not filename or '.' not in filename:
            filename = f"video_{int(time.time())}.mp4"
        
        # Sanitize filename
        return sanitize_filename(filename)
    
    except Exception as e:
        print(f"Filename extraction error: {e}")
        return f"video_{int(time.time())}.mp4"

def safe_file_path(user_id: int, filename: str) -> str:
    """Generate safe file path"""
    try:
        if not filename or not isinstance(filename, str):
            filename = f"video_{int(time.time())}.mp4"
        
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        os.makedirs(user_download_dir, exist_ok=True)
        
        safe_name = sanitize_filename(filename)
        if not safe_name:
            safe_name = f"video_{int(time.time())}.mp4"
        
        return os.path.join(user_download_dir, safe_name)
    
    except Exception as e:
        print(f"File path generation error: {e}")
        fallback_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        os.makedirs(fallback_dir, exist_ok=True)
        return os.path.join(fallback_dir, f"video_{int(time.time())}.mp4")

async def download_from_url(url: str, user_id: int, status_message=None) -> str:
    """Download file from direct URL with comprehensive error handling"""
    try:
        print(f"Starting URL download: {url}")
        
        # Validate inputs
        if not url or not isinstance(url, str):
            error_msg = "Invalid URL provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        if not user_id:
            error_msg = "Invalid user ID provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        # Generate safe filename and path
        file_name = safe_filename_from_url(url)
        dest_path = safe_file_path(user_id, file_name)
        
        print(f"Download destination: {dest_path}")
        print(f"Filename: {file_name}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                print(f"Response status: {resp.status}")
                
                if resp.status == 200:
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    
                    print(f"Starting download, size: {total_size} bytes")
                    
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
                    
                    # Verify download
                    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                        print(f"Download successful: {dest_path} ({os.path.getsize(dest_path)} bytes)")
                        
                        if status_message:
                            await status_message.edit_text(f"✅ **Downloaded:** `{file_name}`\n\nPreparing to merge...")
                        
                        return dest_path
                    else:
                        error_msg = "Downloaded file is empty or corrupted"
                        print(error_msg)
                        if status_message:
                            await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
                        return None
                else:
                    error_msg = f"HTTP {resp.status} - {resp.reason}"
                    print(f"Download failed: {error_msg}")
                    if status_message:
                        await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
                    return None
    
    except Exception as e:
        error_msg = f"Download exception: {str(e)}"
        print(error_msg)
        if status_message:
            try:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            except:
                pass
        return None

async def download_from_tg(message, user_id: int, status_message=None) -> str:
    """Download file from Telegram with comprehensive error handling"""
    try:
        print(f"Starting Telegram download for user {user_id}")
        
        # Validate inputs
        if not message:
            error_msg = "No message provided for download"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        if not user_id:
            error_msg = "Invalid user ID provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        # Determine file type and get filename
        file_name = None
        if message.video:
            file_name = getattr(message.video, 'file_name', None) or f"telegram_video_{int(time.time())}.mp4"
            print(f"Video file detected: {file_name}")
        elif message.document:
            file_name = getattr(message.document, 'file_name', None) or f"telegram_document_{int(time.time())}.mp4"
            print(f"Document file detected: {file_name}")
        else:
            error_msg = "Message contains no downloadable video or document"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        # Generate safe path
        dest_path = safe_file_path(user_id, file_name)
        print(f"Download destination: {dest_path}")
        
        # Progress callback function
        async def progress_func(current, total):
            try:
                if status_message and total > 0:
                    progress = current / total
                    progress_text = (
                        f"📥 **Downloading from Telegram...**\n"
                        f"➢ `{file_name}`\n"
                        f"➢ {get_progress_bar(progress)} `{progress:.1%}`\n"
                        f"➢ **Size:** `{get_file_size(current)}` / `{get_file_size(total)}`"
                    )
                    await smart_progress_editor(status_message, progress_text)
            except Exception as e:
                print(f"Progress callback error: {e}")
        
        # Download file
        print("Starting Telegram download...")
        file_path = await message.download(
            file_name=dest_path,
            progress=progress_func if status_message else None
        )
        
        print(f"Download completed: {file_path}")
        
        # Verify download
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"Download successful: {file_path} ({os.path.getsize(file_path)} bytes)")
            
            if status_message:
                actual_filename = os.path.basename(file_path)
                await status_message.edit_text(f"✅ **Downloaded:** `{actual_filename}`\n\nPreparing to merge...")
            
            return file_path
        else:
            error_msg = "Download failed or file is empty"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
    except Exception as e:
        error_msg = f"Telegram download exception: {str(e)}"
        print(error_msg)
        if status_message:
            try:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            except:
                pass
        return None

async def download_video(client, file_id: str, file_name: str, user_id: int = None, status_message=None) -> str:
    """Download video from Telegram using client - DEPRECATED, use download_from_tg instead"""
    try:
        print(f"download_video called with file_id: {file_id}, file_name: {file_name}")
        
        # This is a fallback method - prefer download_from_tg
        if not file_id or not isinstance(file_id, str):
            error_msg = "Invalid file_id provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
        
        if not file_name:
            file_name = f"video_{int(time.time())}.mp4"
        
        if user_id:
            download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
            os.makedirs(download_dir, exist_ok=True)
        else:
            download_dir = Config.DOWNLOAD_DIR
        
        safe_filename = sanitize_filename(file_name)
        download_path = os.path.join(download_dir, safe_filename)
        
        print(f"Client download path: {download_path}")
        
        # Progress callback function
        async def progress_func(current, total):
            try:
                if status_message and total > 0:
                    progress = current / total
                    progress_text = (
                        f"📥 **Downloading from Telegram...**\n"
                        f"➢ `{safe_filename}`\n"
                        f"➢ {get_progress_bar(progress)} `{progress:.1%}`\n"
                        f"➢ **Size:** `{get_file_size(current)}` / `{get_file_size(total)}`"
                    )
                    await smart_progress_editor(status_message, progress_text)
            except Exception as e:
                print(f"Progress callback error: {e}")
        
        # Download file
        file_path = await client.download_media(
            file_id, 
            file_name=download_path,
            progress=progress_func if status_message else None
        )
        
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"Client download successful: {file_path}")
            if status_message:
                await status_message.edit_text(f"✅ **Downloaded:** `{safe_filename}`\n\nPreparing to merge...")
            return file_path
        else:
            error_msg = "Client download failed or file is empty"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None
    
    except Exception as e:
        error_msg = f"Client download error: {str(e)}"
        print(error_msg)
        if status_message:
            try:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            except:
                pass
        return None

async def save_thumbnail(client, file_id: str, user_id: int) -> str:
    """Download and save thumbnail"""
    try:
        if not file_id or not user_id:
            return None
        
        thumbnail_path = os.path.join(Config.THUMBNAILS_DIR, f"thumb_{user_id}.jpg")
        await client.download_media(file_id, thumbnail_path)
        
        if os.path.exists(thumbnail_path):
            return thumbnail_path
        return None
    
    except Exception as e:
        print(f"Thumbnail save error: {e}")
        return None

async def clean_temp_files(user_id: int):
    """Clean temporary files for user"""
    try:
        if not user_id:
            return
        
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        
        # Clean download directory
        if os.path.exists(user_download_dir):
            for file in os.listdir(user_download_dir):
                try:
                    file_path = os.path.join(user_download_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Cleaned: {file_path}")
                except Exception as e:
                    print(f"Error cleaning {file}: {e}")
        
        # Clean merged directory (old files)
        if os.path.exists(Config.MERGED_DIR):
            for file in os.listdir(Config.MERGED_DIR):
                if f"merged_{user_id}" in file:
                    try:
                        file_path = os.path.join(Config.MERGED_DIR, file)
                        # Remove files older than 1 hour
                        if os.path.getctime(file_path) < (time.time() - 3600):
                            os.remove(file_path)
                            print(f"Cleaned old merged file: {file_path}")
                    except Exception as e:
                        print(f"Error cleaning merged file {file}: {e}")
    
    except Exception as e:
        print(f"Cleanup error: {e}")

async def get_video_properties(video_path: str) -> dict:
    """Get video properties using FFprobe with error handling"""
    try:
        if not video_path or not isinstance(video_path, str):
            return {}
        
        if not os.path.exists(video_path):
            print(f"Video file does not exist: {video_path}")
            return {}
        
        import asyncio
        import json
        
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and stdout:
            data = json.loads(stdout.decode())
            
            # Extract video properties safely
            duration = 0
            width = 0 
            height = 0
            
            # Get duration from format
            if data.get('format', {}).get('duration'):
                try:
                    duration = float(data['format']['duration'])
                except (ValueError, TypeError):
                    duration = 0
            
            # Get video stream info
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0) or 0
                    height = stream.get('height', 0) or 0
                    break
            
            return {
                'duration': duration,
                'width': width,
                'height': height,
                'format': data.get('format', {}),
                'streams': data.get('streams', [])
            }
        else:
            print(f"FFprobe failed for {video_path}: {stderr.decode() if stderr else 'Unknown error'}")
            return {}
    
    except Exception as e:
        print(f"Video properties error for {video_path}: {e}")
        return {}

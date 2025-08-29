import os
import asyncio
import time
import aiofiles
import aiohttp
from bot.config import Config
from utils.helpers import sanitize_filename, get_file_size, get_progress_bar
import uuid
import json
from contextlib import suppress
from typing import Optional, Dict

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
        url_parts = url.rstrip('/').split('/')
        filename = url_parts[-1] or f"video_{int(time.time())}.mp4"
        if '?' in filename:
            filename = filename.split('?')[0]
        if not filename or '.' not in filename:
            filename = f"video_{int(time.time())}.mp4"
        return sanitize_filename(filename)
    except Exception as e:
        print(f"Filename extraction error: {e}")
        return f"video_{int(time.time())}.mp4"

def safe_file_path(user_id: int, filename: str) -> str:
    """Generate safe file path"""
    try:
        filename = filename if filename and isinstance(filename, str) else f"video_{int(time.time())}.mp4"
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        os.makedirs(user_download_dir, exist_ok=True)
        safe_name = sanitize_filename(filename) or f"video_{int(time.time())}.mp4"
        return os.path.join(user_download_dir, safe_name)
    except Exception as e:
        print(f"File path generation error: {e}")
        fallback_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        os.makedirs(fallback_dir, exist_ok=True)
        return os.path.join(fallback_dir, f"video_{int(time.time())}.mp4")

async def download_from_url(url: str, user_id: int, status_message=None) -> Optional[str]:
    """Download file from direct URL with comprehensive error handling and async IO"""
    try:
        print(f"Starting URL download: {url}")
        if not url or not isinstance(url, str):
            error_msg = "Invalid URL provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}\nURL: `{url}`")
            return None
        if not user_id:
            error_msg = "Invalid user ID provided"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None

        file_name = safe_filename_from_url(url)
        dest_path = safe_file_path(user_id, file_name)
        print(f"Download destination: {dest_path}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                print(f"HTTP status: {resp.status}")
                if resp.status == 200:
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    async with aiofiles.open(dest_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
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
                    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                        print(f"Download successful: {dest_path} ({os.path.getsize(dest_path)} bytes)")
                        if status_message:
                            await status_message.edit_text(f"✅ **Downloaded:** `{file_name}`\n\nPreparing to merge...")
                        return dest_path
                    else:
                        error_msg = f"Downloaded file is empty or corrupted\nURL: `{url}`"
                        print(error_msg)
                        if status_message:
                            await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
                        return None
                else:
                    error_msg = f"HTTP {resp.status} - {resp.reason}\nURL: `{url}`"
                    print(f"Download failed: {error_msg}")
                    if status_message:
                        await status_message.edit_text(
                            f"❌ **Download Failed!**\n"
                            f"URL: `{url}`\n"
                            f"HTTP status: {resp.status} - {resp.reason}\n"
                            f"Please check that your URL is valid, accessible, and a direct video file."
                        )
                    return None
    except Exception as e:
        error_msg = f"Download exception: {str(e)}\nURL: `{url}`"
        print(error_msg)
        if status_message:
            with suppress(Exception):
                await status_message.edit_text(
                    f"❌ **Download Failed!**\n"
                    f"{error_msg}\n"
                    f"Please check the URL and your internet connection."
                )
        return None
async def download_from_tg(message, user_id: int, status_message=None) -> Optional[str]:
    """Download file from Telegram with comprehensive error handling"""
    try:
        print(f"Starting Telegram download for user {user_id}")
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

        file_name = None
        if getattr(message, "video", None):
            file_name = getattr(message.video, 'file_name', None) or f"telegram_video_{int(time.time())}.mp4"
        elif getattr(message, "document", None):
            file_name = getattr(message.document, 'file_name', None) or f"telegram_document_{int(time.time())}.mp4"
        else:
            error_msg = "Message contains no downloadable video or document"
            print(error_msg)
            if status_message:
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
            return None

        dest_path = safe_file_path(user_id, file_name)
        print(f"Download destination: {dest_path}")

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

        file_path = await message.download(
            file_name=dest_path,
            progress=progress_func if status_message else None
        )
        print(f"Download completed: {file_path}")

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
            with suppress(Exception):
                await status_message.edit_text(f"❌ **Download Failed!**\n{error_msg}")
        return None

async def clean_temp_files(user_id: int):
    """Clean temporary files for user"""
    try:
        if not user_id:
            return
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        if os.path.exists(user_download_dir):
            for file in os.listdir(user_download_dir):
                with suppress(Exception):
                    file_path = os.path.join(user_download_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Cleaned: {file_path}")
        if os.path.exists(Config.MERGED_DIR):
            cutoff = time.time() - 3600
            for file in os.listdir(Config.MERGED_DIR):
                if f"merged_{user_id}" in file:
                    file_path = os.path.join(Config.MERGED_DIR, file)
                    with suppress(Exception):
                        if os.path.getctime(file_path) < cutoff:
                            os.remove(file_path)
                            print(f"Cleaned old merged file: {file_path}")
    except Exception as e:
        print(f"Cleanup error: {e}")

async def get_video_properties(video_path: str) -> Dict:
    """Get video properties using FFprobe with error handling"""
    try:
        if not video_path or not isinstance(video_path, str):
            return {}
        if not os.path.exists(video_path):
            print(f"Video file does not exist: {video_path}")
            return {}
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
            duration = 0
            width = 0
            height = 0
            if data.get('format', {}).get('duration'):
                with suppress(ValueError, TypeError):
                    duration = float(data['format']['duration'])
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

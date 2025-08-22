"""
File management utilities
"""

import os
import aiofiles
import asyncio
from typing import Optional
from pyrogram import Client
from bot.config import Config

async def download_video(client: Client, file_id: str, file_name: str) -> Optional[str]:
    """
    Download video file from Telegram
    """
    try:
        # Create unique filename to avoid conflicts
        timestamp = int(asyncio.get_event_loop().time())
        safe_filename = f"{timestamp}_{file_name}"
        download_path = os.path.join(Config.DOWNLOAD_DIR, safe_filename)
        
        # Download file
        await client.download_media(file_id, file_name=download_path)
        
        if os.path.exists(download_path):
            return download_path
        else:
            return None
    
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

async def save_thumbnail(client: Client, file_id: str, user_id: int) -> Optional[str]:
    """
    Save thumbnail image for user
    """
    try:
        thumbnail_filename = f"thumb_{user_id}.jpg"
        thumbnail_path = os.path.join(Config.THUMBNAILS_DIR, thumbnail_filename)
        
        # Download thumbnail
        await client.download_media(file_id, file_name=thumbnail_path)
        
        if os.path.exists(thumbnail_path):
            return thumbnail_path
        else:
            return None
    
    except Exception as e:
        print(f"Error saving thumbnail: {e}")
        return None

async def clean_temp_files(user_id: int):
    """
    Clean temporary files for specific user
    """
    try:
        # Clean download files
        for filename in os.listdir(Config.DOWNLOAD_DIR):
            if f"_{user_id}_" in filename or filename.startswith(f"{user_id}_"):
                file_path = os.path.join(Config.DOWNLOAD_DIR, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # Clean merged files
        for filename in os.listdir(Config.MERGED_DIR):
            if f"merged_{user_id}_" in filename:
                file_path = os.path.join(Config.MERGED_DIR, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    except Exception as e:
        print(f"Error cleaning temp files: {e}")

async def clean_old_files():
    """
    Clean files older than 1 hour
    """
    try:
        import time
        current_time = time.time()
        
        # Clean download directory
        for filename in os.listdir(Config.DOWNLOAD_DIR):
            file_path = os.path.join(Config.DOWNLOAD_DIR, filename)
            if os.path.exists(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > 3600:  # 1 hour
                    os.remove(file_path)
        
        # Clean merged directory
        for filename in os.listdir(Config.MERGED_DIR):
            file_path = os.path.join(Config.MERGED_DIR, filename)
            if os.path.exists(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > 3600:  # 1 hour
                    os.remove(file_path)
    
    except Exception as e:
        print(f"Error cleaning old files: {e}")

def get_file_size_string(size_bytes: int) -> str:
    """
    Convert bytes to human readable format
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

async def read_file_async(file_path: str) -> bytes:
    """
    Read file asynchronously
    """
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return b""

async def write_file_async(file_path: str, data: bytes):
    """
    Write file asynchronously
    """
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)
    except Exception as e:
        print(f"Error writing file: {e}")

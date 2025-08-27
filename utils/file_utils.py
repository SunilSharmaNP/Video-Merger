"""
File utility functions
"""

import os
import aiofiles
import aiohttp
from bot.config import Config
from utils.helpers import sanitize_filename

async def download_video(client, file_id: str, file_name: str) -> str:
    """Download video file"""
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(file_name)
        download_path = os.path.join(Config.DOWNLOAD_DIR, safe_filename)
        
        # Download file
        await client.download_media(file_id, download_path)
        
        if os.path.exists(download_path):
            return download_path
        return None
    
    except Exception as e:
        print(f"Download error: {e}")
        return None

async def save_thumbnail(client, file_id: str, user_id: int) -> str:
    """Download and save thumbnail"""
    try:
        thumbnail_path = os.path.join(Config.THUMBNAILS_DIR, f"thumb_{user_id}.jpg")
        
        # Download thumbnail
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
        # Clean download directory
        for file in os.listdir(Config.DOWNLOAD_DIR):
            if str(user_id) in file:
                try:
                    os.remove(os.path.join(Config.DOWNLOAD_DIR, file))
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

async def download_file(url: str, file_path: str) -> bool:
    """Download file from URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    return True
        return False
    except Exception as e:
        print(f"URL download error: {e}")
        return False

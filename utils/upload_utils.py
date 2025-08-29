"""
Advanced upload utility functions with GoFile integration
"""

import aiohttp
import os
import time
import asyncio
from random import choice
from bot.config import Config
from utils.helpers import get_file_size, get_progress_bar
from utils.file_utils import get_video_properties

# Throttling for progress updates
last_edit_time = {}
EDIT_THROTTLE_SECONDS = 4.0

async def smart_progress_editor(status_message, text: str):
    """Throttled editor to prevent FloodWait errors"""
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

class GoFileUploader:
    """Advanced GoFile uploader"""
    
    def __init__(self, token=None):
        self.api_url = "https://api.gofile.io/"
        self.token = token or Config.GOFILE_TOKEN
    
    async def get_server(self):
        """Get optimal upload server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}servers") as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    
                    if result.get("status") == "ok":
                        return choice(result["data"]["servers"])["name"]
                    
                    raise Exception("Failed to fetch GoFile upload server.")
        
        except Exception as e:
            print(f"GoFile server selection error: {e}")
            return "store1"  # Fallback server
    
    async def upload_file(self, file_path: str, status_message=None):
        """Upload file to GoFile"""
        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if status_message:
                await status_message.edit_text("☁️ **Getting Upload Server...**")
            
            server = await self.get_server()
            upload_url = f"https://{server}.gofile.io/uploadFile"
            
            if status_message:
                await status_message.edit_text("☁️ **Uploading to GoFile...**")
            
            # Prepare form data
            data = aiohttp.FormData()
            if self.token:
                data.add_field("token", self.token)
            
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            with open(file_path, "rb") as f:
                data.add_field("file", f, filename=file_name)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data=data) as resp:
                        resp.raise_for_status()
                        resp_json = await resp.json()
                        
                        if resp_json.get("status") == "ok":
                            download_page = resp_json["data"]["downloadPage"]
                            
                            if status_message:
                                await status_message.edit_text(
                                    f"✅ **Upload to GoFile Successful!**\n\n"
                                    f"📁 **File:** `{file_name}`\n"
                                    f"📊 **Size:** `{get_file_size(file_size)}`"
                                )
                            
                            return download_page
                        else:
                            raise Exception(f"GoFile upload failed: {resp_json.get('status')}")
        
        except Exception as e:
            if status_message:
                await status_message.edit_text(f"❌ **GoFile Upload Failed!**\nError: `{str(e)}`")
            print(f"GoFile upload error: {e}")
            return None

async def upload_large_file(file_path: str, status_message=None) -> str:
    """Upload large file to cloud service"""
    try:
        # Try GoFile first
        gofile_uploader = GoFileUploader()
        result = await gofile_uploader.upload_file(file_path, status_message)
        
        if result:
            return result
        
        # If GoFile fails, try anonymous upload
        return await upload_to_gofile_anonymous(file_path, status_message)
    
    except Exception as e:
        print(f"Large file upload error: {e}")
        return None

async def upload_to_gofile_anonymous(file_path: str, status_message=None) -> str:
    """Upload file to GoFile anonymously"""
    try:
        if status_message:
            await status_message.edit_text("☁️ **Trying Anonymous Upload...**")
        
        async with aiohttp.ClientSession() as session:
            # Get upload server
            async with session.get('https://api.gofile.io/getServer') as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                server = data['data']['server']
            
            # Upload file
            with open(file_path, 'rb') as file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', file, filename=os.path.basename(file_path))
                
                async with session.post(f'https://{server}.gofile.io/uploadFile', data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['status'] == 'ok':
                            return result['data']['downloadPage']
        
        return None
    
    except Exception as e:
        print(f"GoFile anonymous upload error: {e}")
        return None

async def upload_to_telegram(client, chat_id: int, file_path: str, status_message, custom_filename: str = None):
    """Upload file to Telegram with enhanced features (no thumbnail logic)"""
    try:
        # Get video metadata
        metadata = await get_video_properties(file_path)
        duration = metadata.get('duration', 0) if metadata else 0
        width = metadata.get('width', 0) if metadata else 0
        height = metadata.get('height', 0) if metadata else 0
        
        final_filename = f"{custom_filename or 'merged_video'}.mkv"
        file_size = os.path.getsize(file_path)
        caption = f"**File:** `{final_filename}`\n**Size:** `{get_file_size(file_size)}`"
        
        # Progress callback
        async def progress(current, total):
            progress_percent = current / total
            progress_text = f"📤 **Uploading to Telegram...**\n➢ {get_progress_bar(progress_percent)} `{progress_percent:.1%}`"
            await smart_progress_editor(status_message, progress_text)
        
        # Upload video (NO thumbnail)
        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=caption,
            file_name=final_filename,
            duration=duration,
            width=width,
            height=height,
            progress=progress
        )
        
        await status_message.delete()
        return True
    
    except Exception as e:
        await status_message.edit_text(f"❌ **Upload Failed!**\nError: `{e}`")
        return False

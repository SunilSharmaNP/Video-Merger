"""
Advanced upload utility functions with GoFile integration and Telegram upload
"""

import aiohttp
import os
import time
import asyncio
from random import choice
from bot.config import Config
from utils.helpers import get_file_size, get_progress_bar
from utils.file_utils import get_video_properties # Assuming get_video_properties is in file_utils

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
            # Suppress exceptions, e.g., if message was deleted or FloodWait
            pass

async def create_default_thumbnail(video_path: str) -> str | None:
    """
    Creates a default thumbnail for a video using FFmpeg.
    """
    thumbnail_path = f"{os.path.splitext(video_path)[0]}.jpg"
    
    # Get video properties to determine a suitable thumbnail time
    metadata = await get_video_properties(video_path)
    if not metadata or not metadata.get("duration"):
        print(f"Could not get duration for '{video_path}'. Skipping default thumbnail creation.")
        return None
    
    # Take a screenshot at half the video's duration
    thumbnail_time = metadata["duration"] / 2
    
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', # Suppress verbose output
        '-i', video_path, 
        '-ss', str(thumbnail_time), # Seek to the middle of the video
        '-vframes', '1', # Take only one frame
        '-c:v', 'mjpeg', # Output as MJPEG (JPEG inside a video container, standard for thumbnails)
        '-f', 'image2', # Force image output format
        '-y', # Overwrite output files without asking
        thumbnail_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    
    if process.returncode != 0:
        print(f"Error creating default thumbnail for '{video_path}': {stderr.decode().strip()}")
        return None
    
    return thumbnail_path if os.path.exists(thumbnail_path) else None

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
                        # Choose a random server from the list
                        return choice(result["data"]["servers"])["name"]
                    
                    raise Exception("Failed to fetch GoFile upload server.")
        
        except Exception as e:
            print(f"GoFile server selection error: {e}")
            return "store1"  # Fallback to a common server if API fails
    
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
                await smart_progress_editor(status_message, "☁️ **Uploading to GoFile...**")
            
            # Prepare form data
            data = aiohttp.FormData()
            if self.token:
                data.add_field("token", self.token)
            
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Open the file in binary read mode
            with open(file_path, "rb") as f:
                # Add the file to the form data
                data.add_field("file", f, filename=file_name)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data=data) as resp:
                        resp.raise_for_status() # Raise an exception for bad status codes
                        resp_json = await resp.json()
                        
                        if resp_json.get("status") == "ok":
                            download_page = resp_json["data"]["downloadPage"]
                            
                            if status_message:
                                await status_message.edit_text(
                                    f"✅ **Upload to GoFile Successful!**\n\n"
                                    f"📁 **File:** `{file_name}`\n"
                                    f"📊 **Size:** `{get_file_size(file_size)}`\n"
                                    f"🔗 **Link:** {download_page}"
                                )
                            
                            return download_page
                        else:
                            raise Exception(f"GoFile upload failed: {resp_json.get('status')} - {resp_json.get('message', 'No specific error message.')}")
        
        except Exception as e:
            # Use suppress for the status_message edit to prevent secondary failures
            if status_message:
                await smart_progress_editor(status_message, f"❌ **GoFile Upload Failed!**\nError: `{str(e)}`")
            print(f"GoFile upload error: {e}")
            return None

async def upload_large_file(file_path: str, status_message=None) -> str:
    """Upload large file to cloud service (GoFile first, then anonymous fallback)"""
    try:
        # Try GoFile with token first
        gofile_uploader = GoFileUploader()
        result = await gofile_uploader.upload_file(file_path, status_message)
        
        if result:
            return result
        
        # If GoFile fails or no token, try anonymous upload
        return await upload_to_gofile_anonymous(file_path, status_message)
    
    except Exception as e:
        print(f"Large file upload error: {e}")
        # Use suppress for the status_message edit to prevent secondary failures
        if status_message:
            await smart_progress_editor(status_message, f"❌ **Large File Upload Failed!**\nError: `{str(e)}`")
        return None

async def upload_to_gofile_anonymous(file_path: str, status_message=None) -> str:
    """Upload file to GoFile anonymously"""
    try:
        if status_message:
            await smart_progress_editor(status_message, "☁️ **Trying Anonymous GoFile Upload...**")
        
        async with aiohttp.ClientSession() as session:
            # Get upload server anonymously
            async with session.get('https://api.gofile.io/getServer') as response:
                response.raise_for_status()
                data = await response.json()
                if data['status'] != 'ok':
                    raise Exception(f"Failed to get anonymous GoFile server: {data.get('message', 'Unknown error')}")
                server = data['data']['server']
            
            # Upload file
            with open(file_path, 'rb') as file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', file, filename=os.path.basename(file_path))
                
                async with session.post(f'https://{server}.gofile.io/uploadFile', data=form_data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    if result['status'] == 'ok':
                        if status_message:
                            await status_message.edit_text(
                                f"✅ **Anonymous GoFile Upload Successful!**\n\n"
                                f"📁 **File:** `{os.path.basename(file_path)}`\n"
                                f"📊 **Size:** `{get_file_size(os.path.getsize(file_path))}`\n"
                                f"🔗 **Link:** {result['data']['downloadPage']}"
                            )
                        return result['data']['downloadPage']
                    else:
                        raise Exception(f"Anonymous GoFile upload failed: {result.get('status')} - {result.get('message', 'No specific error message.')}")
        
        return None
    
    except Exception as e:
        print(f"GoFile anonymous upload error: {e}")
        if status_message:
            await smart_progress_editor(status_message, f"❌ **Anonymous GoFile Upload Failed!**\nError: `{str(e)}`")
        return None

async def upload_to_telegram(client, chat_id: int, file_path: str, status_message, custom_thumbnail: str | None = None, custom_filename: str = None):
    """
    Upload file to Telegram with enhanced features including default thumbnail creation.
    """
    is_default_thumb_created = False
    thumb_to_upload = custom_thumbnail
    try:
        if not thumb_to_upload:
            if status_message:
                await smart_progress_editor(status_message, "🖼️ Analyzing video to create default thumbnail...")
            thumb_to_upload = await create_default_thumbnail(file_path)
            if thumb_to_upload:
                is_default_thumb_created = True

        metadata = await get_video_properties(file_path)
        duration = metadata.get('duration', 0)
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)

        # Ensure filename has .mkv extension if it's a video
        final_filename = custom_filename or os.path.basename(file_path)
        if not final_filename.lower().endswith(('.mkv', '.mp4', '.mov', '.webm', '.avi')):
            # Assume it should be .mkv for merged videos if no specific extension
            final_filename = f"{os.path.splitext(final_filename)[0]}.mkv"
        
        file_size = os.path.getsize(file_path)
        caption = f"**File:** `{final_filename}`\n**Size:** `{get_file_size(file_size)}`"

        async def progress(current, total):
            progress_percent = current / total
            progress_text = (
                f"📤 **Uploading to Telegram...**\n"
                f"➢ {get_progress_bar(progress_percent)} `{progress_percent:.1%}`\n"
                f"➢ **Size:** `{get_file_size(current)}` / `{get_file_size(total)}`"
            )
            await smart_progress_editor(status_message, progress_text)

        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=caption,
            file_name=final_filename,
            duration=int(duration), # Duration should be an integer
            width=width,
            height=height,
            thumb=thumb_to_upload,
            progress=progress
        )
        
        # Delete the progress message if upload is successful
        if status_message:
            await status_message.delete()
        return True
    
    except Exception as e:
        print(f"Telegram upload error: {e}")
        if status_message:
            # Use smart_progress_editor for error messages too, and suppress potential errors
            await smart_progress_editor(status_message, f"❌ **Upload Failed!**\nError: `{str(e)}`")
        return False
    finally:
        # Clean up the default thumbnail if it was created
        if is_default_thumb_created and thumb_to_upload and os.path.exists(thumb_to_upload):
            try:
                os.remove(thumb_to_upload)
                print(f"Cleaned up default thumbnail: {thumb_to_upload}")
            except Exception as e:
                print(f"Error cleaning up thumbnail {thumb_to_upload}: {e}")

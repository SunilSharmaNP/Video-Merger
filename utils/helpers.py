"""
Helper functions for the bot
"""

import asyncio
import time
from typing import Union

def format_duration(seconds: int) -> str:
    """
    Format duration from seconds to human readable format
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds}s"

def get_file_size(size_bytes: int) -> str:
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

def progress_bar(current: int, total: int, length: int = 20) -> str:
    """
    Create a progress bar string
    """
    percent = current / total
    filled_length = int(length * percent)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}] {percent:.1%}"

async def run_command(command: list, timeout: int = 300) -> tuple:
    """
    Run a system command asynchronously
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        return process.returncode, stdout.decode(), stderr.decode()
    
    except asyncio.TimeoutError:
        process.kill()
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations
    """
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    return filename

def is_admin(user_id: int) -> bool:
    """
    Check if user is admin
    """
    from bot.config import Config
    return user_id in Config.SUDO_USERS

def get_timestamp() -> int:
    """
    Get current timestamp
    """
    return int(time.time())

def format_file_info(file_info: dict) -> str:
    """
    Format file information for display
    """
    name = file_info.get('file_name', 'Unknown')
    size = get_file_size(file_info.get('file_size', 0))
    duration = format_duration(file_info.get('duration', 0))
    
    return f"📁 **{name}**\n📏 Size: {size}\n⏱ Duration: {duration}"

async def send_long_message(client, chat_id: int, text: str, max_length: int = 4096):
    """
    Send long message by splitting if necessary
    """
    if len(text) <= max_length:
        await client.send_message(chat_id, text)
    else:
        # Split message into chunks
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for chunk in chunks:
            await client.send_message(chat_id, chunk)
            await asyncio.sleep(0.5)  # Avoid flooding

class Timer:
    """Simple timer class for measuring execution time"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        self.start_time = time.time()
    
    def stop(self):
        self.end_time = time.time()
    
    def elapsed(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0
    
    def elapsed_str(self) -> str:
        return format_duration(int(self.elapsed()))

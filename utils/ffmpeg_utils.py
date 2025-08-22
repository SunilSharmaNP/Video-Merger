"""
FFmpeg utilities for video processing
"""

import os
import asyncio
import subprocess
from typing import List, Optional
from bot.config import Config

async def merge_videos(video_paths: List[str], output_path: str, thumbnail_path: Optional[str] = None, progress_msg=None) -> bool:
    """
    Merge multiple videos using FFmpeg
    """
    try:
        if len(video_paths) < 2:
            return False
        
        # Create a temporary file list for FFmpeg concat demuxer
        concat_file = os.path.join(Config.DOWNLOAD_DIR, f"concat_{os.getpid()}.txt")
        
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video_path in video_paths:
                # Escape single quotes and backslashes for FFmpeg
                escaped_path = video_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Copy streams without re-encoding when possible
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+genpts',
            '-y',  # Overwrite output file
            output_path
        ]
        
        # Update progress
        if progress_msg:
            await progress_msg.edit_text(
                "🎬 **Merging Videos with FFmpeg...**\n\n"
                "⚙️ Processing... This may take several minutes for large files."
            )
        
        # Execute FFmpeg command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Clean up concat file
        if os.path.exists(concat_file):
            os.remove(concat_file)
        
        if process.returncode == 0:
            # If thumbnail is provided, add it to the video
            if thumbnail_path and os.path.exists(thumbnail_path):
                await add_thumbnail_to_video(output_path, thumbnail_path)
            
            return True
        else:
            print(f"FFmpeg error: {stderr.decode()}")
            return False
    
    except Exception as e:
        print(f"Error merging videos: {e}")
        if 'concat_file' in locals() and os.path.exists(concat_file):
            os.remove(concat_file)
        return False

async def add_thumbnail_to_video(video_path: str, thumbnail_path: str) -> bool:
    """
    Add thumbnail to video file
    """
    try:
        temp_output = video_path.replace('.mp4', '_thumb.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', thumbnail_path,
            '-c', 'copy',
            '-c:v:1', 'png',
            '-disposition:v:1', 'attached_pic',
            '-y',
            temp_output
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(temp_output):
            # Replace original with thumbnail version
            os.replace(temp_output, video_path)
            return True
        else:
            # Clean up if failed
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
    
    except Exception as e:
        print(f"Error adding thumbnail: {e}")
        return False

async def get_video_info(video_path: str) -> dict:
    """
    Get video information using FFprobe
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            import json
            return json.loads(stdout.decode())
        else:
            return {}
    
    except Exception as e:
        print(f"Error getting video info: {e}")
        return {}

def check_ffmpeg():
    """
    Check if FFmpeg is installed and available
    """
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

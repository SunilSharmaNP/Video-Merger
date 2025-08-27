"""
FFmpeg utility functions for video processing
"""

import asyncio
import os
from typing import List

async def merge_videos(video_paths: List[str], output_path: str, thumbnail_path: str = None, progress_msg=None) -> bool:
    """Merge multiple videos using FFmpeg"""
    try:
        if len(video_paths) < 2:
            return False
        
        # Create file list for FFmpeg
        list_file = output_path.replace('.mp4', '_list.txt')
        
        with open(list_file, 'w') as f:
            for video_path in video_paths:
                f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        # FFmpeg command
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            '-y',  # Overwrite output file
            output_path
        ]
        
        # Update progress
        if progress_msg:
            await progress_msg.edit_text(
                "🎬 **Merging Videos with FFmpeg...**\n\n"
                "⏳ This may take a few minutes depending on video size."
            )
        
        # Run FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Clean up list file
        if os.path.exists(list_file):
            os.remove(list_file)
        
        # Check if merge was successful
        if process.returncode == 0 and os.path.exists(output_path):
            # Add thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                await add_thumbnail(output_path, thumbnail_path)
            
            return True
        else:
            print(f"FFmpeg error: {stderr.decode()}")
            return False
    
    except Exception as e:
        print(f"Merge error: {e}")
        return False

async def add_thumbnail(video_path: str, thumbnail_path: str) -> bool:
    """Add thumbnail to video file"""
    try:
        temp_path = video_path.replace('.mp4', '_temp.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', thumbnail_path,
            '-map', '0',
            '-map', '1',
            '-c', 'copy',
            '-c:v:1', 'png',
            '-disposition:v:1', 'attached_pic',
            '-y',
            temp_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(temp_path):
            # Replace original file
            os.replace(temp_path, video_path)
            return True
        
        return False
    
    except Exception as e:
        print(f"Thumbnail error: {e}")
        return False

async def get_video_info(video_path: str) -> dict:
    """Get video information using FFprobe"""
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
        
        return {}
    
    except Exception as e:
        print(f"Video info error: {e}")
        return {}

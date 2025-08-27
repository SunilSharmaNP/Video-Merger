"""
Advanced FFmpeg utility functions with robust merging
"""

import asyncio
import os
import time
from typing import List
from bot.config import Config
from utils.helpers import get_progress_bar

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

def get_time_left(elapsed_time: float, progress_percent: float) -> str:
    """Calculate estimated time remaining"""
    if progress_percent <= 0:
        return "Calculating..."
    
    total_time = elapsed_time / progress_percent
    time_left = total_time - elapsed_time
    
    if time_left < 60:
        return f"{int(time_left)}s"
    elif time_left < 3600:
        return f"{int(time_left // 60)}m {int(time_left % 60)}s"
    else:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        return f"{hours}h {minutes}m"

async def merge_videos(video_files: List[str], output_path: str, thumbnail_path: str = None, status_message=None) -> bool:
    """
    Advanced video merging with fast mode and robust fallback
    """
    try:
        if len(video_files) < 2:
            return False
        
        user_id = os.path.basename(os.path.dirname(video_files[0]))
        user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
        inputs_file = os.path.join(user_download_dir, "inputs.txt")
        
        # Create inputs file with absolute paths
        with open(inputs_file, 'w', encoding='utf-8') as f:
            for file in video_files:
                abs_path = os.path.abspath(file)
                formatted_path = abs_path.replace("'", "'\\''")
                f.write(f"file '{formatted_path}'\n")
        
        if status_message:
            await status_message.edit_text("🚀 **Starting Merge (Fast Mode)...**\nThis should be quick if videos are compatible.")
        
        # Try fast merge first (copy streams)
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-f', 'concat', '-safe', '0', '-i', inputs_file,
            '-c', 'copy', '-y', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Check if fast merge succeeded
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if status_message:
                await status_message.edit_text("✅ **Merge Complete! (Fast Mode)**")
            
            # Add thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                await add_thumbnail(output_path, thumbnail_path)
            
            os.remove(inputs_file)
            return True
        else:
            # Fast merge failed, try robust mode
            error_log = stderr.decode().strip()
            print(f"Fast merge failed. FFmpeg stderr: {error_log}")
            
            if status_message:
                await status_message.edit_text(
                    "⚠️ Fast merge failed. Videos might have different formats.\n"
                    "🔄 **Switching to Robust Mode...** This will re-encode videos and may take longer."
                )
                await asyncio.sleep(2)
            
            os.remove(inputs_file)
            return await merge_videos_robust(video_files, output_path, thumbnail_path, status_message)
    
    except Exception as e:
        print(f"Merge error: {e}")
        if status_message:
            await status_message.edit_text(f"❌ **Merge Failed!**\nError: `{str(e)}`")
        return False

async def merge_videos_robust(video_files: List[str], output_path: str, thumbnail_path: str = None, status_message=None) -> bool:
    """Robust merge using filter_complex with progress tracking"""
    try:
        # Get video properties
        tasks = [get_video_info(f) for f in video_files]
        all_properties = await asyncio.gather(*tasks)
        
        valid_durations = []
        for props in all_properties:
            if props and props.get('format', {}).get('duration'):
                try:
                    duration = float(props['format']['duration'])
                    valid_durations.append(duration)
                except (ValueError, TypeError):
                    valid_durations.append(0)
            else:
                valid_durations.append(0)
        
        if len(valid_durations) != len(video_files):
            if status_message:
                await status_message.edit_text("❌ **Merge Failed!** Could not read metadata from one or more videos.")
            return False
        
        total_duration = sum(valid_durations)
        
        if total_duration == 0:
            if status_message:
                await status_message.edit_text("❌ **Merge Failed!** Total video duration is zero.")
            return False
        
        # Build FFmpeg command
        input_args = []
        filter_complex = []
        
        for i, file in enumerate(video_files):
            input_args.extend(['-i', file])
            filter_complex.append(f"[{i}:v:0][{i}:a:0]")
        
        filter_complex_str = "".join(filter_complex) + f"concat=n={len(video_files)}:v=1:a=1[v][a]"
        
        command = [
            'ffmpeg', '-hide_banner', *input_args, '-filter_complex', filter_complex_str,
            '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '23', '-c:a', 'aac', '-b:a', '192k', '-y',
            '-progress', 'pipe:1', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        start_time = time.time()
        
        # Monitor progress
        while process.returncode is None:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break
            
            line = line_bytes.decode('utf-8').strip()
            
            if 'out_time_ms' in line and status_message:
                parts = line.split('=')
                if len(parts) > 1 and parts[1].strip().isdigit():
                    current_time_ms = int(parts[1])
                    if total_duration > 0:
                        progress_percent = max(0, min(1, (current_time_ms / 1000000) / total_duration))
                        elapsed_time = time.time() - start_time
                        
                        progress_text = (
                            f"⚙️ **Merging Videos (Robust Mode)...**\n"
                            f"➢ {get_progress_bar(progress_percent)} `{progress_percent:.1%}`\n"
                            f"➢ **Time Left:** `{get_time_left(elapsed_time, progress_percent)}`"
                        )
                        
                        await smart_progress_editor(status_message, progress_text)
        
        await process.wait()
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if status_message:
                await status_message.edit_text("✅ **Merge Complete! (Robust Mode)**")
            
            # Add thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                await add_thumbnail(output_path, thumbnail_path)
            
            return True
        else:
            stderr = await process.stderr.read()
            error_output = stderr.decode().strip()
            print(f"Robust merge failed. FFmpeg stderr: {error_output}")
            
            if status_message:
                await status_message.edit_text("❌ **Merge Failed!**\nRobust method also failed. See logs for details.")
            
            return False
    
    except Exception as e:
        print(f"Robust merge error: {e}")
        if status_message:
            await status_message.edit_text(f"❌ **Robust Merge Failed!**\nError: `{str(e)}`")
        return False

async def add_thumbnail(video_path: str, thumbnail_path: str) -> bool:
    """Add thumbnail to video file"""
    try:
        temp_path = video_path.replace('.mkv', '_temp.mkv')
        
        command = [
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
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(temp_path):
            os.replace(temp_path, video_path)
            return True
        
        return False
    
    except Exception as e:
        print(f"Thumbnail add error: {e}")
        return False

async def get_video_info(video_path: str) -> dict:
    """Get video information using FFprobe"""
    try:
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
        
        if process.returncode == 0:
            import json
            return json.loads(stdout.decode())
        
        return {}
    
    except Exception as e:
        print(f"Video info error: {e}")
        return {}

"""
Enhanced helper utility functions with null safety
"""

def get_file_size(size_bytes) -> str:
    """Convert bytes to human readable format with null safety"""
    try:
        if size_bytes is None or size_bytes == 0:
            return "0B"
        
        # Ensure it's a number
        if not isinstance(size_bytes, (int, float)):
            return "Unknown"
        
        size_bytes = float(size_bytes)
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    
    except Exception as e:
        print(f"File size format error: {e}")
        return "Unknown"

def format_duration(seconds) -> str:
    """Convert seconds to human readable duration with null safety"""
    try:
        if seconds is None:
            return "0s"
        
        # Ensure it's a number
        if not isinstance(seconds, (int, float)):
            return "Unknown"
        
        seconds = int(seconds)
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs}s"
    
    except Exception as e:
        print(f"Duration format error: {e}")
        return "Unknown"

def get_progress_bar(progress, length: int = 20) -> str:
    """Generate progress bar string with null safety"""
    try:
        if progress is None:
            progress = 0
        
        # Ensure it's a number between 0 and 1
        if not isinstance(progress, (int, float)):
            progress = 0
        
        progress = max(0, min(1, float(progress)))
        filled = int(length * progress)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"
    
    except Exception as e:
        print(f"Progress bar error: {e}")
        return "[░░░░░░░░░░░░░░░░░░░░]"

def sanitize_filename(filename) -> str:
    """Sanitize filename for safe file operations with null safety"""
    try:
        if not filename or not isinstance(filename, str):
            return f"file_{int(time.time())}"
        
        import re
        import time
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        filename = re.sub(r'_{2,}', '_', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:200-len(ext)-1] + ('.' + ext if ext else '')
        
        # Ensure it's not empty
        if not filename:
            filename = f"file_{int(time.time())}"
        
        return filename
    
    except Exception as e:
        print(f"Filename sanitization error: {e}")
        import time
        return f"file_{int(time.time())}"

def get_time_left(elapsed_time, progress_percent) -> str:
    """Calculate estimated time remaining with null safety"""
    try:
        if elapsed_time is None or progress_percent is None:
            return "Calculating..."
        
        if not isinstance(elapsed_time, (int, float)) or not isinstance(progress_percent, (int, float)):
            return "Calculating..."
        
        if progress_percent <= 0:
            return "Calculating..."
        
        total_time = elapsed_time / progress_percent
        time_left = total_time - elapsed_time
        
        if time_left < 0:
            return "Almost done..."
        
        if time_left < 60:
            return f"{int(time_left)}s"
        elif time_left < 3600:
            return f"{int(time_left // 60)}m {int(time_left % 60)}s"
        else:
            hours = int(time_left // 3600)
            minutes = int((time_left % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    except Exception as e:
        print(f"Time calculation error: {e}")
        return "Calculating..."

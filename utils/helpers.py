"""
Enhanced helper utility functions
"""

def get_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """Convert seconds to human readable duration"""
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

def get_progress_bar(progress: float, length: int = 20) -> str:
    """Generate progress bar string"""
    filled = int(length * progress)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_{2,}', '_', filename)
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:200-len(ext)-1] + ('.' + ext if ext else '')
    
    return filename.strip()

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

"""
Configuration management for Video Merge Bot
"""

import os
from typing import List

class Config:
    # Telegram API Configuration
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Bot Owner Configuration
    BOT_OWNER = int(os.environ.get("BOT_OWNER", "0"))
    
    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///users.db")
    
    # File Upload Configuration
    GOFILE_TOKEN = os.environ.get("GOFILE_TOKEN", "")
    STREAMTAPE_API_USERNAME = os.environ.get("STREAMTAPE_API_USERNAME", "")
    STREAMTAPE_API_PASS = os.environ.get("STREAMTAPE_API_PASS", "")
    
    # File Size Limits (in bytes)
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "2147483648"))  # 2GB
    LARGE_FILE_THRESHOLD = int(os.environ.get("LARGE_FILE_THRESHOLD", "2147483648"))  # 2GB
    
    # Temporary Directories
    DOWNLOAD_DIR = "downloads"
    MERGED_DIR = "merged"
    THUMBNAILS_DIR = "thumbnails"
    
    # Bot Messages
    START_TEXT = """👋 **Welcome to Video Merge Bot!**

🎬 **Features:**
• Merge Multiple Videos
• Custom Thumbnail Support  
• Broadcast Messages to Users
• Upload Large Files to Cloud

📝 **How to Use:**
1. Send me 2 or more video files
2. I'll merge them for you
3. Get your merged video instantly!

**Developer:** @AbirHasan2005
**Modified by:** @SunilSharmaNP

💡 Use /help for more information"""

    HELP_TEXT = """🆘 **Help - Video Merge Bot**

**Available Commands:**
• `/start` - Start the bot
• `/help` - Show this help message
• `/merge` - Merge videos (send videos then use this)
• `/cancel` - Cancel current operation
• `/set_thumbnail` - Set custom thumbnail
• `/del_thumbnail` - Delete custom thumbnail
• `/broadcast` - Broadcast message (Owner only)
• `/stats` - Show bot statistics (Owner only)

**How to Merge Videos:**
1. Send 2 or more video files to the bot
2. Use `/merge` command
3. Wait for processing
4. Download your merged video!

**Supported Formats:**
• MP4, AVI, MOV, MKV, FLV, WMV
• Maximum file size: 2GB per video

**Need Support?** Join our support group!"""

    # Admin Users
    SUDO_USERS: List[int] = []
    if os.environ.get("SUDO_USERS"):
        SUDO_USERS = [int(x.strip()) for x in os.environ.get("SUDO_USERS", "").split(",") if x.strip()]
    
    # Add bot owner to sudo users
    if BOT_OWNER not in SUDO_USERS and BOT_OWNER != 0:
        SUDO_USERS.append(BOT_OWNER)
    
    @staticmethod
    def validate_config():
        """Validate essential configuration"""
        if not Config.API_ID or not Config.API_HASH or not Config.BOT_TOKEN:
            raise ValueError("API_ID, API_HASH, and BOT_TOKEN must be provided!")
        
        if not Config.BOT_OWNER:
            raise ValueError("BOT_OWNER must be provided!")
        
        return True

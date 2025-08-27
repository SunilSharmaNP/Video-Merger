"""
Bot configuration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Required Telegram credentials
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Bot owner
    BOT_OWNER = int(os.getenv("BOT_OWNER", 0))
    
    # Admin users
    SUDO_USERS = []
    if os.getenv("SUDO_USERS"):
        SUDO_USERS = [int(x.strip()) for x in os.getenv("SUDO_USERS").split(",") if x.strip().isdigit()]
    
    # Add bot owner to sudo users
    if BOT_OWNER and BOT_OWNER not in SUDO_USERS:
        SUDO_USERS.append(BOT_OWNER)
    
    # File size limits
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 2147483648))  # 2GB
    LARGE_FILE_THRESHOLD = int(os.getenv("LARGE_FILE_THRESHOLD", 2000000000))  # 2GB
    
    # Upload service tokens
    GOFILE_TOKEN = os.getenv("GOFILE_TOKEN", "")
    STREAMTAPE_API_USERNAME = os.getenv("STREAMTAPE_API_USERNAME", "")
    STREAMTAPE_API_PASS = os.getenv("STREAMTAPE_API_PASS", "")
    
    # Directory paths
    DOWNLOAD_DIR = "downloads"
    MERGED_DIR = "merged"
    THUMBNAILS_DIR = "thumbnails"
    DATABASE_PATH = "data/users.db"
    
    # Bot messages
    START_TEXT = """
🎬 **Welcome to Video Merge Bot!**

I can help you merge multiple videos into one file quickly and easily.

**Features:**
• Merge unlimited videos
• Custom thumbnails
• High-quality output
• Fast processing
• Cloud upload for large files

**Quick Test:** Send `/ping` to test if I'm working!

Send me some videos to get started!
"""
    
    HELP_TEXT = """
🆘 **How to use Video Merge Bot:**

**Step by Step:**
1️⃣ Send me 2 or more videos
2️⃣ Click "Merge Videos" button
3️⃣ Wait for processing
4️⃣ Download your merged video

**Commands:**
• `/start` - Start the bot
• `/help` - Show this help
• `/merge` - Merge uploaded videos
• `/cancel` - Cancel current operation
• `/ping` - Test bot response
• `/set_thumbnail` - Set custom thumbnail
• `/del_thumbnail` - Delete custom thumbnail

**Note:** Maximum file size is 2GB per video.
"""
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        if not cls.API_ID or not cls.API_HASH or not cls.BOT_TOKEN:
            raise ValueError("Missing required environment variables: API_ID, API_HASH, BOT_TOKEN")
        if not cls.BOT_OWNER:
            raise ValueError("Missing BOT_OWNER environment variable")
        return True

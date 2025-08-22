"""
Video Merge Bot - Enhanced Version
Based on AbirHasan2005's VideoMerge-Bot design
Modified for SunilSharmaNP/Video repository
"""

import asyncio
import logging
import os
import sys
from pyrogram import Client
from bot.config import Config
from bot.client import bot_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

LOGGER = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        LOGGER.info("🚀 Starting Video Merge Bot...")
        
        # Create necessary directories
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("merged", exist_ok=True)
        os.makedirs("thumbnails", exist_ok=True)
        
        # Start the bot
        await bot_client.start()
        
        # Get bot information
        me = await bot_client.get_me()
        LOGGER.info(f"✅ Bot @{me.username} started successfully!")
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except Exception as e:
        LOGGER.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("🛑 Bot stopped by user")
    except Exception as e:
        LOGGER.error(f"❌ Bot crashed: {e}")

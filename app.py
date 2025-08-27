"""
Video Merge Bot - Complete Working Version
"""

import uvloop
uvloop.install()

import asyncio
import logging
import os
import sys
from pyrogram import Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
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
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Import and start bot
        from bot.client import bot_client
        
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

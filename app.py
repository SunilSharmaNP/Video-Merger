"""
Video Merge Bot - Complete Working Version (thumbnail logic removed)
"""

import uvloop
uvloop.install()

import asyncio
import logging
import os
import sys
from pyrogram import Client # Pyrogram Client को यहां सीधे इम्पोर्ट करने की आवश्यकता नहीं है क्योंकि यह bot.client से आता है।
                           # हालाँकि, यह कोई त्रुटि नहीं है, बस एक अनावश्यक इम्पोर्ट है।

# --- Logging Setup ---
# Logging configuration को एक फ़ंक्शन में encapsulate करना अधिक स्वच्छ है।
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

LOGGER = setup_logging()
# --- End Logging Setup ---

async def main():
    """Main function to start the bot"""
    bot_client = None # bot_client को पहले ही इनिशियलाइज़ कर लें ताकि finally ब्लॉक में इसका उपयोग किया जा सके।
    try:
        LOGGER.info("🚀 Starting Video Merge Bot...")
        
        # Create necessary directories
        LOGGER.info("Creating necessary directories...")
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("merged", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        # Removed: os.makedirs("thumbnails", exist_ok=True)
        
        # Import and start bot
        # 'bot.client' से 'bot_client' को इम्पोर्ट करें
        from bot.client import bot_client
        
        await bot_client.start()
        
        # Get bot information
        me = await bot_client.get_me()
        LOGGER.info(f"✅ Bot @{me.username} started successfully with ID: {me.id}!")
        
        # Keep the bot running indefinitely until stopped
        await asyncio.Event().wait()
        
    except Exception as e:
        LOGGER.error(f"❌ Failed to start bot: {e}", exc_info=True) # exc_info=True स्टैक ट्रेस प्रिंट करेगा।
        sys.exit(1)
    finally:
        if bot_client and bot_client.is_running:
            LOGGER.info("👋 Stopping bot client...")
            await bot_client.stop()
            LOGGER.info("Bot client stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("🛑 Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        LOGGER.error(f"❌ Bot crashed outside main: {e}", exc_info=True)
        sys.exit(1)

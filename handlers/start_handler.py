"""
Start command, help, ping, cancel, and ID command handlers.
"""

import asyncio
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session, clear_user_session # clear_user_session को भी इम्पोर्ट करें
from bot.config import Config
from database.users_db import add_user, get_user_count, init_database # get_user_count की आवश्यकता केवल stats callback में होगी

LOGGER = logging.getLogger(__name__)

# Initialize database on module load.
# It's better to ensure this runs successfully before the bot truly starts.
# We'll rely on app.py's robust startup for this or ensure init_database logs errors.
# For now, this is a common pattern.
asyncio.create_task(init_database())
LOGGER.info("Database initialization task scheduled.")

@bot_client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Handle /start command: greets user and provides main menu."""
    user = message.from_user
    LOGGER.info(f"User {user.id} ({user.first_name}) started the bot.")
    
    # Add user to database (or update if already exists)
    await add_user(user.id, user.first_name, user.username)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats") # Ensure stats callback is handled in callback_handler.py
        ],
        [
            InlineKeyboardButton("👨‍💻 Developer", url=Config.DEVELOPER_URL if hasattr(Config, 'DEVELOPER_URL') else "https://t.me/AbirHasan2005"),
            InlineKeyboardButton("📢 Updates", url=Config.UPDATES_CHANNEL_URL if hasattr(Config, 'UPDATES_CHANNEL_URL') else "https://t.me/Discovery_Updates")
        ]
    ])
    
    start_text = Config.START_TEXT if hasattr(Config, 'START_TEXT') else "👋 Hello! I am a video merger bot."
    
    await message.reply_text(
        start_text,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    """Handle /help command: provides help information."""
    user = message.from_user
    LOGGER.info(f"User {user.id} ({user.first_name}) requested help.")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
    ])
    
    help_text = Config.HELP_TEXT if hasattr(Config, 'HELP_TEXT') else "This bot helps you merge multiple videos."
    
    await message.reply_text(
        help_text,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    """Handle /ping command: checks bot's responsiveness."""
    user = message.from_user
    LOGGER.info(f"User {user.id} ({user.first_name}) sent /ping.")
    await message.reply_text("🏓 **Pong!** Bot is working perfectly!", quote=True)

@bot_client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client, message: Message):
    """Handle /cancel command: aborts current merge operation and clears session."""
    user_id = message.from_user.id
    LOGGER.info(f"User {user_id} ({message.from_user.first_name}) sent /cancel.")
    
    session = get_user_session(user_id)
    
    if session["videos"] or session["merge_in_progress"]: # Check if there's anything active
        clear_user_session(user_id) # Use the centralized function
        await message.reply_text(
            "ℹ️ **Operation Cancelled!**\n\n"
            "All pending videos have been cleared and any ongoing merge task stopped. You can start fresh now!",
            quote=True
        )
    else:
        await message.reply_text(
            "ℹ️ **No Active Operation to Cancel**\n\n"
            "You don't have any pending merge operation.",
            quote=True
        )

@bot_client.on_message(filters.command("id") & filters.private)
async def id_command(client, message: Message):
    """Handle /id command: provides user's Telegram ID."""
    user = message.from_user
    LOGGER.info(f"User {user.id} ({user.first_name}) requested their ID.")
    await message.reply_text(f"🆔 **Your ID:** `{user.id}`\n\n"
                             f"**Chat ID:** `{message.chat.id}`", quote=True) # Chat ID भी उपयोगी हो सकता है

"""
Start command handler
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import Config
from bot.client import bot_client, get_user_session
from database.users_db import add_user, get_user_count

@bot_client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    await add_user(user.id, user.first_name, user.username)
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/AbirHasan2005"),
            InlineKeyboardButton("📢 Updates", url="https://t.me/Discovery_Updates")
        ]
    ])
    
    await message.reply_text(
        Config.START_TEXT,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
    ])
    
    await message.reply_text(
        Config.HELP_TEXT,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client: Client, message: Message):
    """Handle /cancel command"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if session["videos"]:
        session["videos"].clear()
        session["merge_in_progress"] = False
        await message.reply_text(
            "❌ **Operation Cancelled!**\n\n"
            "All pending videos have been cleared. You can start fresh now!",
            quote=True
        )
    else:
        await message.reply_text(
            "ℹ️ **No Operation to Cancel**\n\n"
            "You don't have any pending merge operation.",
            quote=True
        )
        

"""
Start command handler
"""

import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import bot_client, get_user_session
from bot.config import Config
from database.users_db import add_user, get_user_count, init_database

# Initialize database on module load
asyncio.create_task(init_database())

@bot_client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Handle /start command"""
    user = message.from_user
    await add_user(user.id, user.first_name, user.username)
    
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
async def help_command(client, message: Message):
    """Handle /help command"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
    ])
    
    await message.reply_text(
        Config.HELP_TEXT,
        reply_markup=keyboard,
        quote=True
    )

@bot_client.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    """Test command"""
    await message.reply_text("🏓 **Pong!** Bot is working perfectly!")

@bot_client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client, message: Message):
    """Cancel current operation"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    
    if session["videos"]:
        session["videos"].clear()
        session["merge_in_progress"] = False
        await message.reply_text(
            "ℹ️ **Operation Cancelled!**\n\n"
            "All pending videos have been cleared. You can start fresh now!",
            quote=True
        )
    else:
        await message.reply_text(
            "ℹ️ **No Operation to Cancel**\n\n"
            "You don't have any pending merge operation.",
            quote=True
        )
@bot_client.on_message(filters.command("id") & filters.private)
async def id_command(client, message: Message):
    """Get user ID"""
    await message.reply_text(f"🆔 **Your ID:** `{message.from_user.id}`")

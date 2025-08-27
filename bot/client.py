"""
Bot client initialization
"""

from pyrogram import Client
from pyrogram.enums import ParseMode
from bot.config import Config

# Validate configuration
Config.validate_config()

# Initialize the bot client
bot_client = Client(
    name="VideoMergeBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN,
    plugins=dict(root="handlers"),
    workdir="data"
)

# User sessions storage
user_sessions = {}
merge_tasks = {}

def get_user_session(user_id: int) -> dict:
    """Get user session data"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "videos": [],
            "merge_in_progress": False,
            "thumbnail": None
        }
    return user_sessions[user_id]

def clear_user_session(user_id: int):
    """Clear user session data"""
    if user_id in user_sessions:
        del user_sessions[user_id]
    if user_id in merge_tasks:
        del merge_tasks[user_id]

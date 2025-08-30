"""
Bot client initialization and session management.
"""

import logging
from pyrogram import Client
from pyrogram.enums import ParseMode
from bot.config import Config

# Setup logging for this module
LOGGER = logging.getLogger(__name__)

# Validate configuration before initializing the client
LOGGER.info("Validating bot configuration...")
try:
    Config.validate_config()
    LOGGER.info("Configuration validated successfully.")
except Exception as e:
    LOGGER.critical(f"❌ Configuration validation failed: {e}. Exiting.")
    # Configuration के बिना बॉट नहीं चल सकता, इसलिए यहीं क्रैश करना उचित है।
    import sys
    sys.exit(1)

# Initialize the bot client
LOGGER.info("Initializing Pyrogram bot client...")
bot_client = Client(
    name="SanaMergeBot", # Bot का नाम Config से लेना बेहतर हो सकता है अगर यह कॉन्फिगरेबल हो।
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN,
    plugins=dict(root="handlers"),
    workdir="data" # Session files और DB को स्टोर करने के लिए।
)
LOGGER.info("Pyrogram bot client initialized.")

# User sessions storage and merge task management
# Dictionary keys: user_id (int)
# user_sessions values: dict containing "videos", "merge_in_progress", "thumbnail"
user_sessions = {}
# merge_tasks values: asyncio.Task object for ongoing merges (if any)
merge_tasks = {}

# Asyncio Locks for thread-safe access to user_sessions and merge_tasks (optional but good practice for large scale)
# import asyncio
# _user_sessions_lock = asyncio.Lock()
# _merge_tasks_lock = asyncio.Lock()


def get_user_session(user_id: int) -> dict:
    """
    Get or create user session data for a given user_id.
    Ensures that a session dict exists for the user.
    """
    if user_id not in user_sessions:
        LOGGER.debug(f"Creating new session for user_id: {user_id}")
        user_sessions[user_id] = {
            "videos": [],
            "merge_in_progress": False,
            "thumbnail": None
        }
    else:
        LOGGER.debug(f"Retrieving existing session for user_id: {user_id}")
    return user_sessions[user_id]


def clear_user_session(user_id: int):
    """
    Clear user session data and any associated merge tasks for a given user_id.
    """
    if user_id in user_sessions:
        LOGGER.info(f"Clearing session data for user_id: {user_id}")
        del user_sessions[user_id]
    
    if user_id in merge_tasks:
        LOGGER.info(f"Canceling and deleting merge task for user_id: {user_id}")
        # Optionally cancel the task if it's still running
        # if not merge_tasks[user_id].done():
        #     merge_tasks[user_id].cancel()
        del merge_tasks[user_id]
    else:
        LOGGER.debug(f"No active session or merge task found for user_id: {user_id} to clear.")

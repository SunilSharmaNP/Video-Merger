"""
User database management
"""

import aiosqlite
import logging
from bot.config import Config

LOGGER = logging.getLogger(__name__)

async def init_database():
    """Initialize the database"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT 0
                )
            """)
            await db.commit()
        LOGGER.info("Database initialized successfully")
    except Exception as e:
        LOGGER.error(f"Database initialization error: {e}")

async def add_user(user_id: int, first_name: str, username: str = None):
    """Add a new user to database"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, first_name, username)
                VALUES (?, ?, ?)
            """, (user_id, first_name, username))
            await db.commit()
    except Exception as e:
        LOGGER.error(f"Error adding user {user_id}: {e}")

async def get_user_count():
    """Get total user count"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        LOGGER.error(f"Error getting user count: {e}")
        return 0

async def ban_user(user_id: int):
    """Ban a user"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()
    except Exception as e:
        LOGGER.error(f"Error banning user {user_id}: {e}")

async def unban_user(user_id: int):
    """Unban a user"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
    except Exception as e:
        LOGGER.error(f"Error unbanning user {user_id}: {e}")

async def is_user_banned(user_id: int):
    """Check if user is banned"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            async with db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return bool(result[0]) if result else False
    except Exception as e:
        LOGGER.error(f"Error checking ban status for {user_id}: {e}")
        return False

async def get_all_users():
    """Get all non-banned users"""
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cursor:
                return [row[0] for row in await cursor.fetchall()]
    except Exception as e:
        LOGGER.error(f"Error getting all users: {e}")
        return []

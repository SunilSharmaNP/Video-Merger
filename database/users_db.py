"""
User database management
"""

import sqlite3
import aiosqlite
import asyncio
from typing import List, Optional, Tuple

class UserDatabase:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    username TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    total_merges INTEGER DEFAULT 0
                )
            """)
            
            # Create merge history table  
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merge_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    video_count INTEGER NOT NULL,
                    total_size INTEGER NOT NULL,
                    merge_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    async def add_user(self, user_id: int, first_name: str, username: Optional[str] = None):
        """Add or update user in database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO users 
                       (user_id, first_name, username, last_active) 
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                    (user_id, first_name, username)
                )
                await db.commit()
        except Exception as e:
            print(f"Error adding user: {e}")
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = FALSE")
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"Error getting user count: {e}")
            return 0
    
    async def get_all_users(self) -> List[int]:
        """Get all user IDs"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT user_id FROM users WHERE is_banned = FALSE")
                users = await cursor.fetchall()
                return [user[0] for user in users]
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    async def ban_user(self, user_id: int, reason: str = "No reason provided"):
        """Ban a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET is_banned = TRUE, ban_reason = ? WHERE user_id = ?",
                    (reason, user_id)
                )
                await db.commit()
        except Exception as e:
            print(f"Error banning user: {e}")
    
    async def unban_user(self, user_id: int):
        """Unban a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET is_banned = FALSE, ban_reason = NULL WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
        except Exception as e:
            print(f"Error unbanning user: {e}")
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT is_banned FROM users WHERE user_id = ?",
                    (user_id,)
                )
                result = await cursor.fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            print(f"Error checking ban status: {e}")
            return False
    
    async def add_merge_record(self, user_id: int, video_count: int, total_size: int, success: bool):
        """Add merge history record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO merge_history 
                       (user_id, video_count, total_size, success) 
                       VALUES (?, ?, ?, ?)""",
                    (user_id, video_count, total_size, success)
                )
                
                # Update user's total merge count
                if success:
                    await db.execute(
                        "UPDATE users SET total_merges = total_merges + 1 WHERE user_id = ?",
                        (user_id,)
                    )
                
                await db.commit()
        except Exception as e:
            print(f"Error adding merge record: {e}")
    
    async def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get user info
                cursor = await db.execute(
                    "SELECT first_name, username, join_date, total_merges FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user_info = await cursor.fetchone()
                
                if not user_info:
                    return {}
                
                # Get merge history
                cursor = await db.execute(
                    "SELECT COUNT(*), SUM(total_size) FROM merge_history WHERE user_id = ? AND success = TRUE",
                    (user_id,)
                )
                merge_stats = await cursor.fetchone()
                
                return {
                    "name": user_info[0],
                    "username": user_info[1],
                    "join_date": user_info[2],
                    "total_merges": user_info[3] or 0,
                    "total_size_processed": merge_stats[1] or 0
                }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}

# Global database instance
user_db = UserDatabase()

# Convenience functions
async def add_user(user_id: int, first_name: str, username: Optional[str] = None):
    await user_db.add_user(user_id, first_name, username)

async def get_user_count() -> int:
    return await user_db.get_user_count()

async def get_all_users() -> List[int]:
    return await user_db.get_all_users()

async def ban_user(user_id: int, reason: str = "No reason provided"):
    await user_db.ban_user(user_id, reason)

async def unban_user(user_id: int):
    await user_db.unban_user(user_id)

async def is_user_banned(user_id: int) -> bool:
    return await user_db.is_user_banned(user_id)

async def add_merge_record(user_id: int, video_count: int, total_size: int, success: bool):
    await user_db.add_merge_record(user_id, video_count, total_size, success)

async def get_user_stats(user_id: int) -> dict:
    return await user_db.get_user_stats(user_id)

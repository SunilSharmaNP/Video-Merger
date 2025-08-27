"""
Broadcast functionality for admins
"""

from pyrogram import filters
from pyrogram.types import Message
from bot.client import bot_client
from bot.config import Config
from database.users_db import get_all_users
import asyncio

@bot_client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client, message: Message):
    """Broadcast message to all users"""
    user_id = message.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await message.reply_text("❌ **Access Denied!** You are not authorized to use this command.")
        return
    
    if not message.reply_to_message:
        await message.reply_text(
            "📢 **Broadcast Command**\n\n"
            "Reply to a message with `/broadcast` to send it to all users.\n\n"
            "**Usage:** Reply to any message with `/broadcast`"
        )
        return
    
    broadcast_msg = message.reply_to_message
    users = await get_all_users()
    
    if not users:
        await message.reply_text("❌ **No users found in database.**")
        return
    
    status_msg = await message.reply_text(
        f"📢 **Broadcasting to {len(users)} users...**\n\n"
        "⏳ Please wait..."
    )
    
    success = 0
    failed = 0
    
    for user_id in users:
        try:
            await broadcast_msg.copy(user_id)
            success += 1
            await asyncio.sleep(0.1)  # Small delay to avoid rate limits
        except Exception:
            failed += 1
        
        # Update status every 50 users
        if (success + failed) % 50 == 0:
            await status_msg.edit_text(
                f"📢 **Broadcasting...**\n\n"
                f"✅ **Sent:** {success}\n"
                f"❌ **Failed:** {failed}\n"
                f"⏳ **Remaining:** {len(users) - success - failed}"
            )
    
    # Final status
    await status_msg.edit_text(
        f"📢 **Broadcast Completed!**\n\n"
        f"✅ **Successfully sent:** {success}\n"
        f"❌ **Failed:** {failed}\n"
        f"👥 **Total users:** {len(users)}"
    )

@bot_client.on_message(filters.command("ban") & filters.private)
async def ban_user_command(client, message: Message):
    """Ban a user"""
    user_id = message.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await message.reply_text("❌ **Access Denied!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/ban user_id`")
        return
    
    try:
        target_user_id = int(message.command[1])
        from database.users_db import ban_user
        await ban_user(target_user_id)
        await message.reply_text(f"✅ **User {target_user_id} has been banned.**")
    except ValueError:
        await message.reply_text("❌ **Invalid user ID.**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

@bot_client.on_message(filters.command("unban") & filters.private)
async def unban_user_command(client, message: Message):
    """Unban a user"""
    user_id = message.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await message.reply_text("❌ **Access Denied!**")
        return
    
    if len(message.command) < 2:
        await message.reply_text("**Usage:** `/unban user_id`")
        return
    
    try:
        target_user_id = int(message.command[1])
        from database.users_db import unban_user
        await unban_user(target_user_id)
        await message.reply_text(f"✅ **User {target_user_id} has been unbanned.**")
    except ValueError:
        await message.reply_text("❌ **Invalid user ID.**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

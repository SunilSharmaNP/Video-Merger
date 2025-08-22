"""
Broadcast functionality plugin
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.client import bot_client
from database.users_db import get_all_users
from utils.helpers import send_long_message

@bot_client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handle broadcast command (Admin only)"""
    user_id = message.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await message.reply_text(
            "❌ **Access Denied**\n\n"
            "Only authorized users can use this command.",
            quote=True
        )
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        await message.reply_text(
            "📢 **Broadcast Message**\n\n"
            "Reply to a message with `/broadcast` to send it to all users.\n\n"
            "**Usage:** Reply to any message and use this command.",
            quote=True
        )
        return
    
    # Get the message to broadcast
    broadcast_message = message.reply_to_message
    
    # Confirm broadcast
    confirm_text = (
        "📢 **Confirm Broadcast**\n\n"
        "Are you sure you want to send this message to all users?\n\n"
        "**Preview:**\n"
        f"{broadcast_message.text[:200] if broadcast_message.text else 'Media Message'}{'...' if broadcast_message.text and len(broadcast_message.text) > 200 else ''}"
    )
    
    await message.reply_text(confirm_text, quote=True)
    
    # Start broadcast
    await start_broadcast(client, message, broadcast_message)

async def start_broadcast(client: Client, command_message: Message, broadcast_message: Message):
    """Start broadcasting message to all users"""
    try:
        # Get all users
        all_users = await get_all_users()
        total_users = len(all_users)
        
        if total_users == 0:
            await command_message.reply_text("❌ No users found in database!", quote=True)
            return
        
        # Create progress message
        progress_msg = await command_message.reply_text(
            f"📢 **Broadcasting Started**\n\n"
            f"👥 **Total Users:** {total_users}\n"
            f"✅ **Sent:** 0\n"
            f"❌ **Failed:** 0\n"
            f"⏳ **Progress:** 0%",
            quote=True
        )
        
        sent_count = 0
        failed_count = 0
        
        # Broadcast to all users
        for i, user_id in enumerate(all_users):
            try:
                # Forward the message
                if broadcast_message.text:
                    await client.send_message(user_id, broadcast_message.text)
                elif broadcast_message.photo:
                    await client.send_photo(
                        user_id, 
                        broadcast_message.photo.file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.video:
                    await client.send_video(
                        user_id,
                        broadcast_message.video.file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.document:
                    await client.send_document(
                        user_id,
                        broadcast_message.document.file_id,
                        caption=broadcast_message.caption
                    )
                else:
                    # Copy message
                    await broadcast_message.copy(user_id)
                
                sent_count += 1
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to send to {user_id}: {e}")
            
            # Update progress every 50 users
            if (i + 1) % 50 == 0 or i + 1 == total_users:
                progress = ((i + 1) / total_users) * 100
                try:
                    await progress_msg.edit_text(
                        f"📢 **Broadcasting in Progress**\n\n"
                        f"👥 **Total Users:** {total_users}\n"
                        f"✅ **Sent:** {sent_count}\n"
                        f"❌ **Failed:** {failed_count}\n"
                        f"⏳ **Progress:** {progress:.1f}%"
                    )
                except:
                    pass
            
            # Small delay to avoid flooding
            await asyncio.sleep(0.1)
        
        # Final status
        await progress_msg.edit_text(
            f"📢 **Broadcast Completed!**\n\n"
            f"👥 **Total Users:** {total_users}\n"
            f"✅ **Successfully Sent:** {sent_count}\n"
            f"❌ **Failed:** {failed_count}\n"
            f"📊 **Success Rate:** {(sent_count/total_users)*100:.1f}%"
        )
        
    except Exception as e:
        await command_message.reply_text(
            f"❌ **Broadcast Failed**\n\n"
            f"Error: `{str(e)}`",
            quote=True
        )

@bot_client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Show bot statistics (Admin only)"""
    user_id = message.from_user.id
    
    if user_id not in Config.SUDO_USERS:
        await message.reply_text(
            "❌ **Access Denied**\n\n"
            "Only authorized users can view statistics.",
            quote=True
        )
        return
    
    try:
        # Get database statistics
        from database.users_db import get_user_count
        
        total_users = await get_user_count()
        
        stats_text = (
            f"📊 **Bot Statistics**\n\n"
            f"👥 **Users:** {total_users}\n"
            f"🤖 **Version:** 2.0 Enhanced\n"
            f"⚡ **Status:** Active\n"
            f"🛠 **Developer:** @SunilSharmaNP\n"
            f"💡 **Based on:** @AbirHasan2005's design"
        )
        
        await message.reply_text(stats_text, quote=True)
        
    except Exception as e:
        await message.reply_text(
            f"❌ **Error Getting Statistics**\n\n`{str(e)}`",
            quote=True
        )

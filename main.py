import os
import uuid
import asyncio
import logging
import sqlite3
import subprocess
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = "8598689441:AAFF1XM4eRVyqv2i4UNQT8hXK_AhQKq50rs"
OWNER_ID = 7410132900
OWNER_LINK = "https://t.me/ARSHU_ME"
SUPPORT_LINK = "https://t.me/+FyY2t3dyZ_szNGI1"

TEMP_DIR = Path("/tmp/voiceshift")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path("bot_data.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str = None, first_name: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()

def add_group(chat_id: int, title: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO groups (chat_id, title)
        VALUES (?, ?)
    """, (chat_id, title))
    conn.commit()
    conn.close()

def is_banned(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def ban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO banned_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_all_groups() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM groups")
    groups = [row[0] for row in c.fetchall()]
    conn.close()
    return groups

def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM banned_users")
    total_banned = c.fetchone()[0]
    conn.close()
    return {
        "users": total_users,
        "groups": total_groups,
        "banned": total_banned
    }

VOICE_FILTERS = {
    "girly": {
        "label": "1️⃣ Girly (Soft & Feminine)",
        "filter": "asetrate=44100*1.25,atempo=0.80,highpass=f=120,lowpass=f=5500,equalizer=f=150:t=q:w=0.5:g=-2,equalizer=f=250:t=q:w=1:g=3,equalizer=f=900:t=q:w=1.5:g=1,equalizer=f=2500:t=q:w=1:g=3,equalizer=f=4000:t=q:w=1:g=2,volume=1.25"
    },
    "anime": {
        "label": "2️⃣ High Pitch (Anime Girl)",
        "filter": "asetrate=44100*1.45,atempo=0.69,highpass=f=150,lowpass=f=6000,equalizer=f=100:t=q:w=0.8:g=-3,equalizer=f=300:t=q:w=1:g=2,equalizer=f=1000:t=q:w=1:g=1,equalizer=f=2800:t=q:w=1:g=4,equalizer=f=4500:t=q:w=1:g=2,volume=1.2"
    },
    "deep_boy": {
        "label": "3️⃣ Deep Boy (Masculine)",
        "filter": "asetrate=44100*0.82,atempo=1.22,highpass=f=80,lowpass=f=3000,equalizer=f=100:t=q:w=1:g=3,equalizer=f=200:t=q:w=0.7:g=2,equalizer=f=500:t=q:w=1:g=-1,volume=1.3"
    },
    "deep_bass": {
        "label": "4️⃣ Deep Bass (Ultra Deep)",
        "filter": "asetrate=44100*0.68,atempo=1.47,highpass=f=60,lowpass=f=2500,equalizer=f=60:t=q:w=0.7:g=5,equalizer=f=120:t=q:w=1:g=4,equalizer=f=300:t=q:w=1:g=-1,volume=1.35"
    }
}

def _process_voice_sync(input_path: Path, output_path: Path, filter_complex: str) -> bool:
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-af", filter_complex,
            "-c:a", "libopus", "-b:a", "64k",
            "-vbr", "on", "-compression_level", "10",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0 and output_path.exists()
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return False
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return False

async def process_voice(input_path: Path, output_path: Path, filter_complex: str) -> bool:
    return await asyncio.to_thread(_process_voice_sync, input_path, output_path, filter_complex)

def cleanup_files(*paths):
    for path in paths:
        try:
            if path and Path(path).exists():
                Path(path).unlink()
        except Exception as e:
            logger.error(f"Cleanup error for {path}: {e}")

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")

async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.forward(chat_id=OWNER_ID)
    except Exception as e:
        logger.error(f"Failed to forward to owner: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    
    add_user(user.id, user.username, user.first_name)
    
    if chat.type in ["group", "supergroup"]:
        add_group(chat.id, chat.title)
    
    intro_text = """🎙️ <b>VoiceShift Bot Ready</b>

Send me a voice message and I will send back 4 versions:
1️⃣ Girly (Soft & Feminine)
2️⃣ High Pitch (Anime Girl)
3️⃣ Deep Boy (Masculine)
4️⃣ Deep Bass (Ultra Deep)

👇 Send a voice note now!"""

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 OWNER", url=OWNER_LINK),
            InlineKeyboardButton("🆘 SUPPORT", url=SUPPORT_LINK)
        ]
    ])
    
    await update.message.reply_text(
        intro_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    notify_text = f"""🆕 <b>New User Started Bot</b>

👤 Name: {user.first_name or 'N/A'}
🔗 Username: @{user.username if user.username else 'N/A'}
🆔 ID: <code>{user.id}</code>
💬 Chat Type: {chat.type}"""
    
    if chat.type in ["group", "supergroup"]:
        notify_text += f"\n📍 Group: {chat.title}"
    
    await notify_owner(context, notify_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return
    
    add_user(user.id, user.username, user.first_name)
    
    if chat.type in ["group", "supergroup"]:
        add_group(chat.id, chat.title)
    
    await forward_to_owner(update, context)
    
    notify_text = f"""🎤 <b>Voice Message Received</b>

👤 From: {user.first_name or 'N/A'}
🔗 Username: @{user.username if user.username else 'N/A'}
🆔 ID: <code>{user.id}</code>
⏱ Duration: {update.message.voice.duration}s"""
    
    await notify_owner(context, notify_text)
    
    processing_msg = await update.message.reply_text("🔄 Processing your voice... Please wait!")
    
    unique_id = str(uuid.uuid4())[:8]
    input_path = TEMP_DIR / f"input_{unique_id}.ogg"
    output_paths = {}
    
    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(input_path)
        
        await update.message.chat.send_action("record_audio")
        
        for key, config in VOICE_FILTERS.items():
            output_path = TEMP_DIR / f"output_{unique_id}_{key}.ogg"
            output_paths[key] = output_path
            
            await update.message.chat.send_action("record_audio")
            success = await process_voice(input_path, output_path, config["filter"])
            
            if success and output_path.exists():
                await update.message.chat.send_action("upload_voice")
                with open(output_path, "rb") as audio_file:
                    await update.message.reply_voice(
                        voice=audio_file,
                        caption=config["label"]
                    )
                    try:
                        await context.bot.send_voice(
                            chat_id=OWNER_ID,
                            voice=audio_file,
                            caption=f"From {user.first_name} (@{user.username}): {config['label']}"
                        )
                    except:
                        pass
            else:
                await update.message.reply_text(f"❌ Failed to generate {config['label']}")
        
        await processing_msg.delete()
        
        await notify_owner(context, f"✅ Voice processing completed for user {user.id}")
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await update.message.reply_text("❌ An error occurred while processing your voice. Please try again.")
        await notify_owner(context, f"❌ Error processing voice from user {user.id}: {str(e)}")
    
    finally:
        cleanup_files(input_path, *output_paths.values())

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        ban_user(target_id)
        await update.message.reply_text(f"✅ User {target_id} has been banned.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        unban_user(target_id)
        await update.message.reply_text(f"✅ User {target_id} has been unbanned.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        return
    
    stats = get_stats()
    
    text = f"""📊 <b>Bot Statistics</b>

👥 Total Users: {stats['users']}
👥 Total Groups: {stats['groups']}
🚫 Banned Users: {stats['banned']}"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        return
    
    reply = update.message.reply_to_message
    broadcast_text = " ".join(context.args) if context.args else None
    
    if not reply and not broadcast_text:
        await update.message.reply_text(
            "📢 <b>Broadcast Usage:</b>\n\n"
            "1️⃣ Reply to any message with /broadcast\n"
            "2️⃣ Or use: /broadcast Your message here",
            parse_mode=ParseMode.HTML
        )
        return
    
    users = get_all_users()
    groups = get_all_groups()
    all_chats = users + groups
    
    if not all_chats:
        await update.message.reply_text("❌ No users or groups to broadcast to.")
        return
    
    status_msg = await update.message.reply_text(f"📤 Broadcasting to {len(all_chats)} chats...")
    
    success = 0
    failed = 0
    
    for chat_id in all_chats:
        try:
            if reply:
                await reply.copy(chat_id=chat_id)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=broadcast_text,
                    parse_mode=ParseMode.HTML
                )
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {chat_id}: {e}")
    
    await status_msg.edit_text(
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}",
        parse_mode=ParseMode.HTML
    )

async def handle_group_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    if chat.type in ["group", "supergroup"]:
        add_group(chat.id, chat.title)
        await notify_owner(
            context,
            f"🆕 <b>Bot added to group</b>\n\n"
            f"📍 Group: {chat.title}\n"
            f"🆔 ID: <code>{chat.id}</code>"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling update: {context.error}")
    
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"⚠️ <b>Bot Error</b>\n\n<code>{str(context.error)[:500]}</code>",
            parse_mode=ParseMode.HTML
        )
    except:
        pass

def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_group_join))
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

# VoiceShift Telegram Bot

## Overview
A production-ready Telegram voice changer bot that processes voice messages and returns 4 different voice variations using FFmpeg audio processing. Designed for Railway deployment via GitHub.

## Features
- **Voice Processing**: Converts voice messages into 4 variations:
  - Girly (Soft & Feminine)
  - High Pitch (Anime Girl)
  - Deep Boy (Masculine)
  - Deep Bass (Ultra Deep)

- **Owner Features**:
  - `/broadcast` - Send messages to all users and groups
  - `/ban <user_id>` - Ban users from using the bot
  - `/unban <user_id>` - Unban users
  - `/stats` - View bot statistics
  - Real-time notifications for all bot activity

- **User Tracking**: SQLite database stores users, groups, and banned list

## Deployment (Railway - Simple 3 Steps)

### Step 1: Download Project
1. Click the **⋯** menu in top right of Replit
2. Select **"Download as ZIP"**
3. Extract on your computer

### Step 2: Upload to GitHub
1. Create new repository on github.com
2. Upload **ONLY these 2 files**:
   - `main.py`
   - `requirements.txt`

### Step 3: Deploy on Railway
1. Go to railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Choose your repository
5. Railway auto-configures and deploys
6. Bot runs 24/7 ✅

**No configuration needed. Railway auto-detects Python, installs FFmpeg, and runs the bot.**

## Bot Configuration
Bot token and owner ID are hardcoded in main.py:
- BOT_TOKEN: `8598689441:AAFF1XM4eRVyqv2i4UNQT8hXK_AhQKq50rs`
- OWNER_ID: `7410132900`

## Commands
- `/start` - Start bot and show welcome message
- `/broadcast` - (Owner only) Broadcast message to all users
- `/ban <id>` - (Owner only) Ban a user
- `/unban <id>` - (Owner only) Unban a user
- `/stats` - (Owner only) View statistics

## Files
```
main.py          - Complete bot code (15KB)
requirements.txt - Dependencies (1 line)
bot_data.db      - Created at runtime (SQLite database)
```

## Tech Stack
- Python 3.11
- python-telegram-bot 21.3
- FFmpeg for audio processing
- SQLite for data storage

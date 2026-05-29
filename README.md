# 🔥 TRX-DDOS Telegram Bot

## Features
- ⚡ Layer 7 DDoS Attack via API
- 👑 Admin & Reseller Panel
- 🔑 Premium/Basic Key System
- 💼 Reseller Token System
- 🎭 Fake Attack System
- 📊 Live Attack Status
- 💾 JSON Backup System

## Deploy on Render

### Step 1: Fork this repo

### Step 2: Create Web Service on Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Health Check Path: `/health`

### Step 3: Add Environment Variable (Optional)
- `TOKEN` = your_bot_token

### Step 4: Keep Alive (24/7)
Use UptimeRobot to ping: `https://your-app.onrender.com/health`

## Commands

### User Commands
- `/attack IP PORT TIME` - Start attack
- `/status` - Check active attacks
- `/myplan` - Check your plan
- `/redeem KEY` - Redeem key
- `/id` - Your ID
- `/rules` - Bot rules
- `/help` - Help menu

### Admin Commands
- `/adduser ID DAYS` - Add user
- `/removeuser ID` - Remove user
- `/alluser` - List all users
- `/genbasic PREFIX DURATION` - Generate basic key
- `/genpremium PREFIX DURATION` - Generate premium key
- `/broadcast MSG` - Broadcast message
- `/getjson` - Backup data

### Reseller Commands
- `/genkey` - Generate keys
- `/deletekey` - Delete keys
- `/blockkey KEY` - Block key
- `/myblockedkeys` - Show blocked keys

## Owner
- Owner ID: 7983241359 (Hidden)

## Support
Contact @TG_ROLEX

## License
MIT
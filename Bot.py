# -*- coding: utf-8 -*-
# ============================================================
#   LEMINH TOOL 
#   CHÀO MỪNG BẠN ĐẾN VỚI TOOL LE MINH
# ============================================================
import os
import re
import json
import math
import html
import time
import random
import string
import hashlib
import asyncio
import logging
from collections import OrderedDict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ============================================================
#   CONFIG
# ============================================================
BOT_TOKEN = "8934734495:AAGVXUK0muIIPK2XYJhzxwHJoaZNbysc-UY"
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 10000))

ADMIN_IDS = [8852639183]
ADMIN_PHONE = "0372834763"

BANK_NAME = "MBBANK"
BANK_ACC = "0372834763"
BANK_OWNER = "LE MINH"

SECRET_TOKEN = "LEMINH_TOOL_VIP_V13_KEY"
SECRET_SALT = "LM13X9K8M7N6P5Q4W3E2R1Z0"

DATA_DIR = "/data"
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(DATA_DIR, "users_db.json")
KEYS_FILE = os.path.join(DATA_DIR, "keys_db.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

LINE = "━━━━━━━━━━━━━"


# ============================================================
#   BẢNG GIÁ
# ============================================================
KEY_PRICING = {
    "1h":      {"price": 3000,   "seconds": 3600,     "label": "1 Giờ"},
    "1day":    {"price": 10000,  "seconds": 86400,    "label": "1 Ngày"},
    "4day":    {"price": 30000,  "seconds": 345600,   "label": "4 Ngày"},
    "1week":   {"price": 50000,  "seconds": 604800,   "label": "1 Tuần"},
    "1month":  {"price": 80000,  "seconds": 2592000,  "label": "1 Tháng"},
    "forever": {"price": 0,      "seconds": -1,       "label": "Vĩnh Viễn"},
}


# ============================================================
#   DATABASE
# ============================================================
def load_db(path):
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=OrderedDict)
    except Exception as e:
        logger.error("Load DB: " + str(e))
        return {}

def save_db(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        logger.error("Save DB: " + str(e))


# ============================================================
#   THUẬT TOÁN MD5 CUSTOM
# ============================================================
def left_rotate(x, amount):
    x &= 0xFFFFFFFF
    return ((x << amount) | (x >> (32 - amount))) & 0xFFFFFFFF

def md5_custom(message):
    T = [int(4294967296 * abs(math.sin(i + 1))) & 0xFFFFFFFF for i in range(64)]
    s = (
        [7, 12, 17, 22] * 4 + [5, 9, 14, 20] * 4 +
        [4, 11, 16, 23] * 4 + [6, 10, 15, 21] * 4
    )
    orig_len_in_bits = (len(message) * 8) & 0xFFFFFFFFFFFFFFFF
    message += b'\x80'
    while (len(message) * 8) % 512 != 448:
        message += b'\x00'
    message += orig_len_in_bits.to_bytes(8, byteorder='little')
    A, B, C, D = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    for offset in range(0, len(message), 64):
        block = message[offset:offset+64]
        M = [int.from_bytes(block[i:i+4], byteorder='little') for i in range(0, 64, 4)]
        a, b, c, d = A, B, C, D
        for i in range(64):
            if i <= 15:
                f = (b & c) | ((~b) & d); g = i
            elif i <= 31:
                f = (d & b) | ((~d) & c); g = (5 * i + 1) % 16
            elif i <= 47:
                f = b ^ c ^ d; g = (3 * i + 5) % 16
            else:
                f = c ^ (b | (~d)); g = (7 * i) % 16
            f = (f + a + T[i] + M[g]) & 0xFFFFFFFF
            a = d; d = c; c = b
            b = (b + left_rotate(f, s[i])) & 0xFFFFFFFF
        A = (A + a) & 0xFFFFFFFF
        B = (B + b) & 0xFFFFFFFF
        C = (C + c) & 0xFFFFFFFF
        D = (D + d) & 0xFFFFFFFF
    return (A.to_bytes(4, 'little') + B.to_bytes(4, 'little') +
            C.to_bytes(4, 'little') + D.to_bytes(4, 'little')).hex()


# ============================================================
#   THUẬT TOÁN TOÁN HỌC v13
#   + Hàm băm mở rộng
#   + Ma trận 4x4 xoay vòng
#   + Dãy Fibonacci mod 100
#   + Số nguyên tố + logarit tự nhiên
#   + Hàm sigmoid để chuẩn hoá
# ============================================================

def prime_sieve(n):
    """Sàng số nguyên tố"""
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = False
    return [i for i, is_p in enumerate(sieve) if is_p]

# Sinh sẵn 1000 số nguyên tố đầu
PRIMES = prime_sieve(8000)[:1000]


def fibonacci_mod(n, m=100):
    """Dãy Fibonacci mod m"""
    a, b = 0, 1
    for _ in range(n % 300):
        a, b = b, (a + b) % m
    return a


def matrix_rotate_4x4(matrix):
    """Xoay ma trận 4x4 90 độ"""
    return [[matrix[3-j][i] for j in range(4)] for i in range(4)]


def matrix_mult_4x4(A, B):
    """Nhân 2 ma trận 4x4 mod 256"""
    return [[sum(A[i][k] * B[k][j] for k in range(4)) % 256 for j in range(4)] for i in range(4)]


def bytes_to_matrix_4x4(data):
    """Chuyển 16 bytes thành ma trận 4x4"""
    return [[data[i * 4 + j] for j in range(4)] for i in range(4)]


def matrix_to_bytes_4x4(matrix):
    """Chuyển ma trận 4x4 thành 16 bytes"""
    out = bytearray()
    for row in matrix:
        for val in row:
            out.append(val % 256)
    return bytes(out)


def sigmoid(x):
    """Hàm sigmoid"""
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def detect_hash_type(h):
    h = h.strip()
    if re.fullmatch(r"[a-fA-F0-9]{32}", h):
        return "MD5"
    if re.fullmatch(r"[a-fA-F0-9]{64}", h):
        return "SHA-256"
    return None


def predict(h):
    h = h.strip()
    htype = detect_hash_type(h)
    if not htype:
        return {"error": True}

    # ============================================
    # BƯỚC 1: Tạo entropy đa tầng
    # ============================================
    md5_c = md5_custom(h.encode())
    sha3_256 = hashlib.sha3_256(h.encode()).hexdigest()
    sha3_512 = hashlib.sha3_512(h.encode()).hexdigest()
    blake2b = hashlib.blake2b(h.encode()).hexdigest()
    blake2s = hashlib.blake2s(h.encode()).hexdigest()
    weight = 47 if htype == "MD5" else 59

    salt1 = "LM13_A"
    salt2 = "SEED_" + str(len(h)) + "_" + str(weight)
    salt3 = "X9K2M7P4Q1"
    salt4 = "R_" + md5_c[:14]
    salt5 = "ZK3L8N5W2Y7"
    salt6 = SECRET_SALT
    salt7 = "OMEGA_" + sha3_256[:10]
    salt8 = "FINAL_" + blake2s[:12]

    # ============================================
    # BƯỚC 2: Trộn + Băm 128 vòng
    # ============================================
    mixed = (h + "::" + SECRET_TOKEN + "::" + md5_c + "::" + sha3_256
             + "::" + sha3_512 + "::" + blake2b + "::" + blake2s
             + "::" + salt1 + "::" + salt2 + "::" + salt3 + "::" + salt4
             + "::" + salt5 + "::" + salt6 + "::" + salt7 + "::" + salt8).encode()

    for i in range(128):
        r = i % 6
        if r == 0:
            mixed = hashlib.sha512(mixed + str(i).encode() + salt1.encode()).digest()
        elif r == 1:
            mixed = hashlib.sha256(mixed + str(i).encode() + salt2.encode()).digest()
        elif r == 2:
            mixed = hashlib.blake2b(mixed + str(i).encode() + salt3.encode()).digest()
        elif r == 3:
            mixed = hashlib.sha3_256(mixed + str(i).encode() + salt4.encode()).digest()
        elif r == 4:
            mixed = hashlib.sha3_512(mixed + str(i).encode() + salt5.encode()).digest()
        else:
            mixed = hashlib.blake2s(mixed + str(i).encode() + salt6.encode()).digest()

    # ============================================
    # BƯỚC 3: AVALANCHE 8 lần
    # ============================================
    avalanche_configs = [
        (13, 0xA5A5A5A5A5A5A5A5), (7, 0x5A5A5A5A5A5A5A5A),
        (11, 0x3C3C3C3C3C3C3C3C), (17, 0xC3C3C3C3C3C3C3C3),
        (19, 0xFFFF0000FFFF0000), (23, 0x0F0F0F0F0F0F0F0F),
        (29, 0xF0F0F0F0F0F0F0F0), (31, 0x1234567890ABCDEF),
    ]
    for shift, mask in avalanche_configs:
        b = int.from_bytes(mixed[:8], "big")
        b = ((b << shift) | (b >> (64 - shift))) & 0xFFFFFFFFFFFFFFFF
        b ^= mask
        mixed = b.to_bytes(8, "big") + mixed[8:]

    # ============================================
    # BƯỚC 4: MA TRẬN 4x4 XOAY VÒNG (TOÁN HỌC)
    # ============================================
    for block_start in range(0, min(64, len(mixed) - 16), 16):
        block = mixed[block_start:block_start + 16]
        if len(block) < 16:
            break
        mat = bytes_to_matrix_4x4(block)
        # Xoay 4 lần + nhân chính nó
        for _ in range(4):
            mat = matrix_rotate_4x4(mat)
        mat2 = matrix_mult_4x4(mat, mat)
        mixed = mixed[:block_start] + matrix_to_bytes_4x4(mat2) + mixed[block_start + 16:]

    # ============================================
    # BƯỚC 5: KHUẾCH TÁN PHI TUYẾN 6 LỚP
    # ============================================
    score = 0
    raw_score = 0
    for i in range(0, len(mixed), 2):
        cb = mixed[i:i + 4]
        if len(cb) < 4:
            cb += b"\x00" * (4 - len(cb))
        ck = int.from_bytes(cb, "big")

        score = (score * weight + (ck * ck) % 9973 + ck) % 100
        score = (score ^ (ck % 97)) % 100
        inv = pow(ck % 89 + 1, 87, 89)
        score = (score + inv) % 100
        inv2 = pow(ck % 101 + 1, 99, 101)
        score = (score * inv2 + 7) % 100
        inv3 = pow(ck % 103 + 1, 101, 103)
        score = (score + inv3 * 3) % 100
        raw_score = (raw_score + ck) % 1000000

    # ============================================
    # BƯỚC 6: SỐ NGUYÊN TỐ + FIBONACCI + LOGARIT (TOÁN HỌC)
    # ============================================
    # Chọn 4 số nguyên tố từ entropy
    p1 = PRIMES[(raw_score) % 1000]
    p2 = PRIMES[(raw_score >> 4) % 1000]
    p3 = PRIMES[(raw_score >> 8) % 1000]
    p4 = PRIMES[(raw_score >> 12) % 1000]

    # Công thức toán học
    prime_score = (p1 * 7 + p2 * 11 + p3 * 13 + p4 * 17) % 100
    score = (score + prime_score) % 100

    # Fibonacci
    fib_n = raw_score % 300
    fib_val = fibonacci_mod(fib_n, 100)
    score = (score + fib_val) % 100

    # Logarit tự nhiên
    try:
        log_val = int(abs(math.log(abs(score) + 1)) * 1000) % 100
        score = (score + log_val) % 100
    except Exception:
        pass

    # Căn bậc 2
    sqrt_val = int(math.sqrt(raw_score + 1) * 100) % 100
    score = (score + sqrt_val) % 100

    # Lượng giác
    sin_val = int(abs(math.sin(score / 10.0)) * 1000) % 100
    cos_val = int(abs(math.cos(raw_score / 1000.0)) * 1000) % 100
    score = (score + sin_val + cos_val) % 100

    # ============================================
    # BƯỚC 7: BIT-MIX 5 NGUỒN
    # ============================================
    fm1 = int.from_bytes(hashlib.sha256(mixed).digest()[:8], "big")
    fm2 = int.from_bytes(hashlib.sha3_256(mixed).digest()[:8], "big")
    fm3 = int.from_bytes(hashlib.blake2b(mixed).digest()[:8], "big")
    fm4 = int.from_bytes(hashlib.blake2s(mixed).digest()[:8], "big")
    fm5 = int.from_bytes(hashlib.sha3_512(mixed).digest()[:8], "big")

    score = (score * 73 + fm1) % 100
    score = (score * 97 + fm2) % 100
    score = (score * 53 + fm3) % 100
    score = (score * 89 + fm4) % 100
    score = (score * 67 + fm5) % 100

    # ============================================
    # BƯỚC 8: MODULAR + XÁO TRỘN
    # ============================================
    score = (score * 101 + 43) % 100
    score = (score ^ 0x5A) % 100
    score = (score + (weight * 7)) % 100
    score = (score * 131 + 17) % 100

    sb = score & 0x7F
    score = ((sb << 1) | (sb >> 6)) & 0x7F
    if score >= 100:
        score = score % 100

    score = abs(score) % 100

    # ============================================
    # BƯỚC 9: TÍNH % TIN CẬY (sigmoid + math)
    # ============================================
    distance = abs(score - 50)  # 0..50

    # Sigmoid cho tin cậy
    sig = sigmoid((distance - 15) / 5.0)  # 0..1
    confidence = 50 + int(sig * 45)        # 50..95

    # Điều chỉnh entropy ±3
    entropy_factor = (raw_score % 7) - 3
    confidence = confidence + entropy_factor

    # Đảm bảo trong khoảng
    confidence = max(50, min(int(confidence), 95))

    # ============================================
    # KẾT QUẢ
    # ============================================
    if 45 <= score <= 55 and confidence < 55:
        result = "CHƯA RÕ"
    else:
        result = "XỈU" if score < 50 else "TÀI"

    return {
        "hash": h,
        "type": htype,
        "result": result,
        "tai": score,
        "xiu": 100 - score,
        "confidence": confidence,
    }


def esc(t):
    return html.escape(str(t))


# ============================================================
#   KEY MANAGEMENT
# ============================================================
def gen_key():
    return "LM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=13))

def create_key(key_type):
    keys = load_db(KEYS_FILE)
    key = gen_key()
    info = KEY_PRICING.get(key_type, KEY_PRICING["1day"])
    keys[key] = {
        "type": key_type, "label": info["label"], "seconds": info["seconds"],
        "created": time.time(), "used_by": None, "used_at": None,
    }
    save_db(KEYS_FILE, keys)
    return key

def activate_key(user_id, key):
    keys = load_db(KEYS_FILE)
    users = load_db(DB_FILE)
    key = key.strip().upper()
    if key not in keys:
        return False, "Key không tồn tại!"
    info = keys[key]
    if info.get("used_by"):
        return False, "Key đã được sử dụng!"
    info["used_by"] = str(user_id)
    info["used_at"] = time.time()
    keys[key] = info
    save_db(KEYS_FILE, keys)
    uid = str(user_id)
    now = time.time()
    if info["seconds"] == -1:
        users[uid] = {
            "key": key, "type": info["type"], "label": info["label"],
            "activated": now, "expires": -1,
        }
    else:
        existing = users.get(uid, {})
        base = existing["expires"] if existing and existing.get("expires", 0) > now else now
        users[uid] = {
            "key": key, "type": info["type"], "label": info["label"],
            "activated": now, "expires": base + info["seconds"],
        }
    save_db(DB_FILE, users)
    return True, info

def check_user(user_id):
    users = load_db(DB_FILE)
    uid = str(user_id)
    if uid not in users:
        return False, None
    u = users[uid]
    if u.get("expires") == -1:
        return True, u
    if u.get("expires", 0) > time.time():
        return True, u
    return False, u

def get_remaining(expires):
    if expires == -1:
        return "Vĩnh viễn ♾️"
    remain = int(expires - time.time())
    if remain <= 0:
        return "Hết hạn"
    d = remain // 86400
    h = (remain % 86400) // 3600
    m = (remain % 3600) // 60
    s = remain % 60
    if d > 0:
        return str(d) + " ngày " + str(h) + " giờ"
    if h > 0:
        return str(h) + " giờ " + str(m) + " phút"
    if m > 0:
        return str(m) + " phút " + str(s) + " giây"
    return str(s) + " giây"

def is_admin(user_id):
    return user_id in ADMIN_IDS


# ============================================================
#   TIN NHẮN KHOÁ
# ============================================================
async def send_locked_message(update_or_msg, is_callback=False):
    text = (
        "🔒 <b>KEY ĐÃ HẾT HẠN</b>\n"
        + LINE + "\n\n"
        "⚠️ Thời gian sử dụng đã kết thúc!\n\n"
        "📋 Để tiếp tục:\n"
        "1️⃣ Gõ /nap xem bảng giá\n"
        "2️⃣ Chuyển khoản MBBANK\n"
        "3️⃣ Nhận key mới từ admin\n"
        "4️⃣ Gõ /key MÃ_KEY để kích hoạt\n\n"
        + LINE + "\n"
        "💎 <b>BẢNG GIÁ:</b>\n"
        "├ 1 Giờ      → 3.000đ\n"
        "├ 1 Ngày     → 10.000đ\n"
        "├ 4 Ngày     → 30.000đ\n"
        "├ 1 Tuần     → 50.000đ\n"
        "├ 1 Tháng    → 80.000đ\n"
        "└ Vĩnh viễn  → Liên hệ\n"
        + LINE + "\n"
        "📞 Zalo: <code>" + ADMIN_PHONE + "</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 MUA KEY", callback_data="nap")],
        [InlineKeyboardButton("🔑 NHẬP KEY", callback_data="huongdan_key")],
        [InlineKeyboardButton("💬 ZALO ADMIN", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    if is_callback:
        await update_or_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update_or_msg.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def send_no_key_message(update_or_msg, is_callback=False):
    text = (
        "🔒 <b>CHƯA KÍCH HOẠT KEY</b>\n"
        + LINE + "\n\n"
        "⚠️ Cần có key VIP để sử dụng!\n\n"
        "📋 Các bước:\n"
        "1️⃣ Gõ /nap xem bảng giá\n"
        "2️⃣ Chuyển khoản MBBANK\n"
        "3️⃣ Nhận key từ admin\n"
        "4️⃣ Gõ /key MÃ_KEY\n\n"
        + LINE + "\n"
        "💎 <b>BẢNG GIÁ:</b>\n"
        "├ 1 Giờ      → 3.000đ\n"
        "├ 1 Ngày     → 10.000đ\n"
        "├ 4 Ngày     → 30.000đ\n"
        "├ 1 Tuần     → 50.000đ\n"
        "├ 1 Tháng    → 80.000đ\n"
        "└ Vĩnh viễn  → Liên hệ\n"
        + LINE + "\n"
        "📞 Zalo: <code>" + ADMIN_PHONE + "</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 MUA KEY", callback_data="nap")],
        [InlineKeyboardButton("🔑 NHẬP KEY", callback_data="huongdan_key")],
        [InlineKeyboardButton("💬 ZALO ADMIN", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    if is_callback:
        await update_or_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update_or_msg.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================
#   HANDLERS - USER
# ============================================================
async def start(update, ctx):
    user = update.effective_user
    users = load_db(DB_FILE)
    uid = str(user.id)
    if uid in users:
        users[uid]["username"] = user.username or ""
        users[uid]["first_name"] = user.first_name or ""
        save_db(DB_FILE, users)

    is_vip, info = check_user(user.id)
    if is_admin(user.id):
        status = "👑 ADMIN"
    elif is_vip:
        status = "✅ VIP - " + get_remaining(info.get("expires", -1))
    elif info is not None:
        status = "🔴 <b>KEY ĐÃ HẾT HẠN</b>"
    else:
        status = "❌ Chưa kích hoạt"

    text = (
        "🎯 <b>LEMINH TOOL VIP v13</b>\n"
        "Dự đoán TÀI / XỈU chuẩn xác\n"
        + LINE + "\n\n"
        "📥 <b>Gửi MD5 (32) / SHA-256 (64)</b>\n"
        "→ Bot tự nhận diện + dự đoán\n\n"
        + LINE + "\n"
        "🔑 <b>Trạng thái:</b> " + status + "\n"
        + LINE + "\n"
        "📋 <b>Lệnh:</b>\n"
        "/key – Kích hoạt key\n"
        "/nap – Nạp tiền mua key\n"
        "/info – Thông tin VIP\n"
        "/hotro – Liên hệ admin\n"
        "/xoa – Xoá tin nhắn bot"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_key(update, ctx):
    args = ctx.args
    if not args:
        text = (
            "🔑 <b>KÍCH HOẠT KEY</b>\n" + LINE + "\n\n"
            "📝 <code>/key MÃ_KEY</code>\n\n"
            "💡 Ví dụ:\n"
            "<code>/key LM-ABCD1234XYZ</code>\n\n"
            "📞 /nap để mua key"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    key = args[0].strip().upper()
    ok, result = activate_key(update.effective_user.id, key)
    if ok:
        text = (
            "✅ <b>KÍCH HOẠT THÀNH CÔNG!</b>\n" + LINE + "\n"
            "🔑 Key: <code>" + esc(key) + "</code>\n"
            "🎁 Loại: <b>" + result["label"] + "</b>\n"
            + LINE + "\n"
            "👉 Gửi MD5 / HASH để dự đoán!"
        )
    else:
        text = "❌ <b>LỖI:</b> " + result
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_nap(update, ctx):
    text = (
        "💳 <b>NẠP TIỀN MUA KEY</b>\n"
        + LINE + "\n"
        "🏦 <b>Ngân hàng:</b> " + BANK_NAME + "\n"
        "💳 <b>Số TK:</b> <code>" + BANK_ACC + "</code>\n"
        "👤 <b>Chủ TK:</b> " + BANK_OWNER + "\n"
        "📝 <b>Nội dung:</b> SĐT Telegram\n\n"
        + LINE + "\n"
        "💎 <b>BẢNG GIÁ:</b>\n"
        "├ 1 Giờ      → 3.000đ\n"
        "├ 1 Ngày     → 10.000đ\n"
        "├ 4 Ngày     → 30.000đ\n"
        "├ 1 Tuần     → 50.000đ\n"
        "├ 1 Tháng    → 80.000đ\n"
        "└ Vĩnh viễn  → Liên hệ\n"
        + LINE + "\n"
        "📞 Gửi bill: <code>" + ADMIN_PHONE + "</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Zalo Admin", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_info(update, ctx):
    user = update.effective_user
    ok, info = check_user(user.id)
    role = "👑 ADMIN" if is_admin(user.id) else "👤 USER"

    if not ok and info is None:
        text = (
            "👤 <b>THÔNG TIN</b>\n" + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🎖️ Vai trò: " + role + "\n"
            "🔑 Key: <b>Chưa kích hoạt</b>\n\n"
            "👉 /key để kích hoạt\n"
            "👉 /nap để mua key"
        )
    elif not ok:
        text = (
            "👤 <b>THÔNG TIN</b>\n" + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🎖️ Vai trò: " + role + "\n"
            "🔑 Key: <code>" + esc(info.get("key", "")) + "</code>\n"
            "🎁 Loại: " + esc(info.get("label", "")) + "\n"
            "🔴 Trạng thái: <b>ĐÃ HẾT HẠN</b>\n\n"
            "👉 /nap để gia hạn"
        )
    else:
        text = (
            "👤 <b>THÔNG TIN VIP</b>\n" + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🎖️ Vai trò: " + role + "\n"
            "🔑 Key: <code>" + esc(info.get("key", "")) + "</code>\n"
            "🎁 Loại: <b>" + esc(info.get("label", "")) + "</b>\n"
            "⏱️ Còn lại: <b>" + get_remaining(info.get("expires", -1)) + "</b>"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_hotro(update, ctx):
    text = (
        "📞 <b>LIÊN HỆ ADMIN</b>\n" + LINE + "\n"
        "• Zalo: <code>" + ADMIN_PHONE + "</code>\n"
        "• SĐT: <code>" + ADMIN_PHONE + "</code>\n\n"
        "💳 /nap – Mua key\n"
        "🔑 /key – Kích hoạt"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Zalo Admin", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_xoa(update, ctx):
    try:
        await update.message.delete()
    except Exception:
        pass
    msg = await ctx.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧹 <b>Đã xoá!</b>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_32(update, ctx):
    text = (
        "📘 <b>HƯỚNG DẪN 32 KÝ TỰ (MD5)</b>\n" + LINE + "\n"
        "• Chuỗi đúng <b>32</b> ký tự hex\n"
        "• Ví dụ:\n"
        "<code>d41d8cd98f00b204e9800998ecf8427e</code>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_64(update, ctx):
    text = (
        "📗 <b>HƯỚNG DẪN 64 KÝ TỰ (SHA-256)</b>\n" + LINE + "\n"
        "• Chuỗi đúng <b>64</b> ký tự hex\n"
        "• Ví dụ:\n"
        "<code>e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855</code>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_myid(update, ctx):
    user = update.effective_user
    text = (
        "🆔 <b>Telegram ID:</b>\n"
        "<code>" + str(user.id) + "</code>\n\n"
        "👤 Tên: " + esc(user.first_name) + "\n"
        "📛 Username: @" + esc(user.username or "không có")
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ============================================================
#   HANDLE HASH - GỌN GÀNG
# ============================================================
async def handle_hash(update, ctx):
    user = update.effective_user
    text = update.message.text.strip()

    users = load_db(DB_FILE)
    uid = str(user.id)
    if uid in users:
        users[uid]["username"] = user.username or ""
        users[uid]["first_name"] = user.first_name or ""
        save_db(DB_FILE, users)

    if not is_admin(user.id):
        is_vip, info = check_user(user.id)
        if info is None:
            await send_no_key_message(update)
            return
        if not is_vip:
            await send_locked_message(update)
            return

    res = predict(text)
    if res.get("error"):
        msg = (
            "❌ <b>SAI ĐỊNH DẠNG!</b>\n" + LINE + "\n"
            "• MD5: 32 ký tự hex\n"
            "• SHA-256: 64 ký tự hex\n\n"
            "👉 /32kitu hoặc /64kitu"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if res["result"] == "TÀI":
        emoji = "🔴"
    elif res["result"] == "XỈU":
        emoji = "🔵"
    else:
        emoji = "⚪"

    is_vip, info = check_user(user.id)
    if is_admin(user.id):
        remain_line = "👑 ADMIN"
    elif info:
        remain_line = "⏱️ Còn: <b>" + get_remaining(info.get("expires", -1)) + "</b>"
    else:
        remain_line = ""

    msg = (
        "🎯 <b>LEMINH VIP</b>\n"
        + LINE + "\n"
        + "🔎 <code>" + esc(res["hash"]) + "</code>\n"
        + "🧩 " + res["type"] + "\n\n"
        + emoji + " <b>" + res["result"] + "</b>\n"
        + "📊 TÀI: <b>" + str(res["tai"]) + "%</b> | XỈU: <b>" + str(res["xiu"]) + "%</b>\n"
        + "🎯 Tin cậy: <b>" + str(res["confidence"]) + "%</b>\n"
        + LINE + "\n"
        + remain_line + "\n"
        + "💰 Chúc bạn thắng lớn!"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ============================================================
#   ADMIN
# ============================================================
async def cmd_admin(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    users = load_db(DB_FILE)
    keys = load_db(KEYS_FILE)
    now = time.time()
    total_users = len(users)
    active_users = sum(1 for u in users.values() if u.get("expires", 0) == -1 or u.get("expires", 0) > now)
    expired_users = total_users - active_users
    total_keys = len(keys)
    used_keys = sum(1 for k in keys.values() if k.get("used_by"))
    unused_keys = total_keys - used_keys

    text = (
        "👑 <b>ADMIN PANEL</b>\n" + LINE + "\n"
        "👥 Tổng user: <b>" + str(total_users) + "</b>\n"
        "✅ VIP hoạt động: <b>" + str(active_users) + "</b>\n"
        "🔴 Đã hết hạn: <b>" + str(expired_users) + "</b>\n"
        "🔑 Tổng key: <b>" + str(total_keys) + "</b>\n"
        "✔️ Đã dùng: <b>" + str(used_keys) + "</b>\n"
        "🆓 Chưa dùng: <b>" + str(unused_keys) + "</b>\n"
        + LINE + "\n"
        "📋 <b>LỆNH ADMIN:</b>\n"
        "├ /users – Danh sách user\n"
        "├ /capkey [loại] [số] – Tạo key\n"
        "├ /keys – Xem key\n"
        "├ /delkey MÃ – Xoá key\n"
        "├ /giahan ID loại – Gia hạn\n"
        "└ /resetkey ID – Reset user"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_capkey(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    args = ctx.args
    if not args:
        text = (
            "🔑 <b>CẤP KEY</b>\n" + LINE + "\n"
            "📝 <code>/capkey [loại] [số]</code>\n\n"
            "📋 Loại:\n"
            "├ <code>1h</code> – 1 Giờ (3k)\n"
            "├ <code>1day</code> – 1 Ngày (10k)\n"
            "├ <code>4day</code> – 4 Ngày (30k)\n"
            "├ <code>1week</code> – 1 Tuần (50k)\n"
            "├ <code>1month</code> – 1 Tháng (80k)\n"
            "└ <code>forever</code> – Vĩnh viễn"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    key_type = args[0].lower()
    if key_type not in KEY_PRICING:
        await update.message.reply_text("❌ Loại key không hợp lệ!")
        return
    qty = 1
    if len(args) > 1:
        try:
            qty = max(1, min(int(args[1]), 50))
        except Exception:
            qty = 1
    keys_created = [create_key(key_type) for _ in range(qty)]
    info = KEY_PRICING[key_type]
    text = (
        "✅ <b>ĐÃ TẠO " + str(qty) + " KEY</b>\n" + LINE + "\n"
        "🎁 Loại: <b>" + info["label"] + "</b>\n"
        "💰 Giá: <b>" + "{:,}".format(info["price"]).replace(",", ".") + "đ</b>\n"
        + LINE + "\n"
        "🔑 <b>DANH SÁCH:</b>\n"
    )
    for k in keys_created:
        text += "<code>" + k + "</code>\n"
    text += "\n💡 Gửi key cho khách."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_users(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    users = load_db(DB_FILE)
    if not users:
        await update.message.reply_text("📋 Chưa có user nào.")
        return
    now = time.time()
    text = "👥 <b>DANH SÁCH USER(</b>\n" + LINE +update "\n"
    items = sorted(users.items(), key.e=lambda x: x[1].get("ffactivated", 0), reverse=True)
    forective uid, u in items[:30]:
        expires = u.get("expires", 0)
        if expires == -1:
            status = "♾️ Vĩnh viễn"
        elif expires > now:
            status = "✅ " + get_remaining(expires)
        else:
            status = "🔴 Hết hạn"
        name = u.get("first_name", "") or u.get("username", "") or "Ẩn danh"
        key = u.get("key", "N/A")
        text += (
            "👤 <b>" + esc(name[:20]) + "</b>\n"
            "   🆔 <code>" + uid + "</code>\n"
            "   🔑 <code>" + esc(key) + "</code>\n"
            "   ⏱️ " + status + "\n\n"
        )
    if len(users) > 30:
        text += "... và " + str(len(users) - 30) + " user khác"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_giahan(update, ctx):
    if not is_admin_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "⏰ <code>/giahan [ID] [loại]</code>",
            parse_mode=ParseMode.HTML
        )
        return
    target_id = args[0].strip()
    key_type = args[1].lower()
    if key_type not in KEY_PRICING:
        await update.message.reply_text("❌ Loại key không hợp lệ!")
        return
    users = load_db(DB_FILE)
    if target_id not in users:
        await update.message.reply_text("❌ User không tồn tại!")
        return
    info = KEY_PRICING[key_type]
    now = time.time()
    u = users[target_id]
    if info["seconds"] == -1:
        u["expires"] = -1
    else:
        base = u["expires"] if u.get("expires", 0) > now else now
        u["expires"] = base + info["seconds"]
    u["type"] = key_type
    u["label"] = info["label"]
    users[target_id] = u
    save_db(DB_FILE, users)
    await update.message.reply_text(
        "✅ <b>GIA HẠN OK</b>\n" + LINE + "\n"
        "🆔 <code>" + target_id + "</code>\n"
        "🎁 " + info["label"] + "\n"
        "⏱️ " + get_remaining(u["expires"]),
        parse_mode=ParseMode.HTML
    )


async def cmd_resetkey(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("📝 /resetkey [ID]")
        return
    target_id = args[0].strip()
    users = load_db(DB_FILE)
    if target_id not in users:
        await update.message.reply_text("❌ User không tồn tại!")
        return
    del users[target_id]
    save_db(DB_FILE, users)
    await update.message.reply_text(
        "✅ Đã reset: <code>" + target_id + "</code>",
        parse_mode=ParseMode.HTML
    )


async def cmd_keys(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    keys = load_db(KEYS_FILE)
    if not keys:
        await update.message.reply_text("📋 Chưa có key nào.")
        return
    used = [(k, v) for k, v in keys.items() if v.get("used_by")]
    unused = [(k, v) for k, v in keys.items() if not v.get("used_by")]
    text = "🔑 <b>QUẢN LÝ KEY</b>\n" + LINE + "\n"
    text += "🆓 Chưa dùng: <b>" + str(len(unused)) + "</b>\n"
    text += "✔️ Đã dùng: <b>" + str(len(used)) + "</b>\n\n"
    text += "🆓 <b>KEY CHƯA DÙNG (20 đầu):</b>\n"
    for k, v in unused[:20]:
        text += "<code>" + k + "</code> [" + v["label"] + "]\n"
    if len(unused) > 20:
        text += "... và " + str(len(unused) - 20) + " key khác\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_delkey(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("📝 /delkey MÃ_KEY")
        return
    key = args[0].strip().upper()
    keys = load_db(KEYS_FILE)
    if key not in keys:
        await update.message.reply_text("❌ Key không tồn tại!")
        return
    del keys[key]
    save_db(KEYS_FILE, keys)
    await update.message.reply_text(
        "✅ Đã xoá: <code>" + esc(key) + "</code>",
        parse_mode=ParseMode.HTML
    )


# ============================================================
#   CALLBACK
# ============================================================
async def button_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "nap":
        await q.message.reply_text(
            "💳 <b>" + BANK_NAME + "</b>\n"
            "Số TK: <code>" + BANK_ACC + "</code>\n"
            "Chủ TK: " + BANK_OWNER + "\n\n"
            "Zalo: <code>" + ADMIN_PHONE + "</code>",
            parse_mode=ParseMode.HTML,
        )
    elif q.data == "huongdan_key":
        await q.message.reply_text(
            "🔑 <code>/key MÃ_KEY</code>\n"
            "Ví dụ: <code>/key LM-ABC123XYZ</code>",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
#   POST INIT
# ============================================================
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Bắt đầu"),
        BotCommand("key", "Kích hoạt key"),
        BotCommand("nap", "Nạp tiền mua key"),
        BotCommand("info", "Thông tin VIP"),
        BotCommand("32kitu", "Hướng dẫn MD5"),
        BotCommand("64kitu", "Hướng dẫn SHA-256"),
        BotCommand("hotro", "Liên hệ admin"),
        BotCommand("xoa", "Xoá tin nhắn bot"),
        BotCommand("myid", "Xem ID Telegram"),
        BotCommand("admin", "Admin panel"),
    ])
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Set commands OK")
    logger.info("💾 DATA_DIR: " + DATA_DIR)


# ============================================================
#   MAIN
# ============================================================
def main():
    if not BOT_TOKEN:
        raise SystemExit("⚠️ Chưa có BOT_TOKEN!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("key", cmd_key))
    app.add_handler(CommandHandler("nap", cmd_nap))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("hotro", cmd_hotro))
    app.add_handler(CommandHandler("xoa", cmd_xoa))
    app.add_handler(CommandHandler("32kitu", cmd_32))
    app.add_handler(CommandHandler("64kitu", cmd_64))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("capkey", cmd_capkey))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("keys", cmd_keys))
    app.add_handler(CommandHandler("delkey", cmd_delkey))
    app.add_handler(CommandHandler("giahan", cmd_giahan))
    app.add_handler(CommandHandler("resetkey", cmd_resetkey))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))

    webhook_url = RENDER_URL + "/" + BOT_TOKEN
    logger.info("🚀 Webhook: " + webhook_url)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

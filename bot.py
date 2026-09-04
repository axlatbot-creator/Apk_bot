# -*- coding: utf-8 -*-
"""
APK Kod Bot — Instagram bloger uchun o'yin tarqatish boti + to'liq Admin Panel
Talab: Python 3.8+, pyTelegramBotAPI
O'rnatish (Pydroid 3 terminalida):
    pip install pyTelegramBotAPI

Ishga tushirish:
    python bot.py

Bot long-polling orqali ishlaydi — hech qanday server, domen yoki SSL
sertifikat kerak emas, telefonda ham to'g'ridan-to'g'ri ishlayveradi.
"""

import sqlite3
import time
import threading
from datetime import datetime

import telebot
from telebot import types

# ============================================================
#                        KONFIGURATSIYA
# ============================================================
BOT_TOKEN = "8761360925:AAFo0Cshuot8M1-DWVJDwdkzL5DMFQsuPeg"
MAIN_ADMIN_ID = 7991544389
DB_PATH = "bot_database.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ============================================================
#                    MA'LUMOTLAR BAZASI (SQLite)
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        joined_at TEXT,
        last_active TEXT
    );

    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        version TEXT,
        size TEXT,
        category TEXT,
        image_file_id TEXT,
        apk_file_id TEXT,
        extra_info TEXT,
        instagram_link TEXT,
        downloads INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game_id INTEGER,
        downloaded_at TEXT
    );

    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        added_by INTEGER,
        added_at TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TEXT
    );
    """)
    conn.commit()

    # Asosiy adminni bazaga qo'shish
    c.execute("INSERT OR IGNORE INTO admins (telegram_id, added_by, added_at) VALUES (?, ?, ?)",
              (MAIN_ADMIN_ID, MAIN_ADMIN_ID, now()))

    # Standart sozlamalar
    defaults = {
        "maintenance_mode": "0",
        "start_message": "👋 Salom, {name}!\n\nInstagram videosidagi kodni yuboring, o'yinni yuklab oling 🎮",
        "force_sub_message": "📢 Botdan foydalanish uchun avval quyidagi kanal(lar)ga obuna bo'ling:",
        "not_found_message": "❌ Bunday kod topilmadi. Kodni tekshirib qaytadan yuboring.",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_setting(key):
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else ""


def set_setting(key, value):
    conn = db()
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()


def log_action(admin_id, action, details=""):
    conn = db()
    conn.execute("INSERT INTO logs (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
                 (admin_id, action, details, now()))
    conn.commit()
    conn.close()


def touch_user(tg_user):
    conn = db()
    row = conn.execute("SELECT id FROM users WHERE telegram_id=?", (tg_user.id,)).fetchone()
    if row:
        conn.execute("UPDATE users SET last_active=?, username=?, first_name=? WHERE telegram_id=?",
                     (now(), tg_user.username, tg_user.first_name, tg_user.id))
    else:
        conn.execute("INSERT INTO users (telegram_id, username, first_name, joined_at, last_active) "
                     "VALUES (?, ?, ?, ?, ?)",
                     (tg_user.id, tg_user.username, tg_user.first_name, now(), now()))
    conn.commit()
    conn.close()


def is_admin(telegram_id):
    conn = db()
    row = conn.execute("SELECT 1 FROM admins WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return row is not None


def is_main_admin(telegram_id):
    return telegram_id == MAIN_ADMIN_ID


# ============================================================
#                    HOLAT (WIZARD) BOSHQARUVI
# ============================================================
# admin_id -> {"flow": str, "step": int, "data": dict, "extra": any}
WIZ = {}

ADD_GAME_STEPS = [
    ("name", "🎮 O'yin nomini kiriting:"),
    ("code", "🔑 Maxsus kodni kiriting (masalan: UZ123):"),
    ("description", "📝 O'yin tavsifini kiriting:"),
    ("version", "📱 Versiyasini kiriting:"),
    ("size", "📦 Hajmini kiriting (masalan: 500 MB):"),
    ("category", "🗂 Kategoriyasini kiriting:"),
    ("image", "🖼 O'yin rasmini yuboring (ixtiyoriy — o'tkazib yuborish uchun /skip yozing):"),
    ("apk", "📁 Endi shu o'yinning APK faylini yuboring:"),
    ("extra_info", "ℹ️ Qo'shimcha ma'lumot (ixtiyoriy — /skip):"),
    ("instagram_link", "🔗 Instagram video havolasi (ixtiyoriy — /skip):"),
]

EDIT_FIELD_LABELS = {
    "name": "Nomi", "description": "Tavsifi", "version": "Versiyasi",
    "size": "Hajmi", "category": "Kategoriyasi", "extra_info": "Qo'shimcha ma'lumot",
    "instagram_link": "Instagram havolasi",
}


# ============================================================
#                        KLAVIATURALAR
# ============================================================

def admin_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ O'yin qo'shish", "📋 O'yinlar")
    kb.row("🔑 Kodlar", "📢 Majburiy obuna")
    kb.row("👥 Foydalanuvchilar", "📊 Statistika")
    kb.row("📣 Xabar yuborish", "⚙️ Sozlamalar")
    kb.row("👑 Adminlar", "📝 Loglar")
    kb.row("💾 Backup", "⬅️ Chiqish")
    return kb


def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("❌ Bekor qilish")
    return kb


def channels_inline_kb(only_unchecked=True):
    conn = db()
    rows = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup()
    for r in rows:
        kb.add(types.InlineKeyboardButton(f"📢 {r['name']}", url=f"https://t.me/{r['username'].lstrip('@')}"))
    kb.add(types.InlineKeyboardButton("✅ OBUNANI TEKSHIRISH", callback_data="checksub"))
    return kb


def game_detail_kb(game_id, admin_view=False):
    kb = types.InlineKeyboardMarkup()
    if admin_view:
        kb.row(
            types.InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"editmenu_{game_id}"),
            types.InlineKeyboardButton("🗑 O'chirish", callback_data=f"delconfirm_{game_id}"),
        )
        kb.row(
            types.InlineKeyboardButton("📊 Statistika", callback_data=f"gamestat_{game_id}"),
            types.InlineKeyboardButton("📁 APK almashtirish", callback_data=f"replaceapk_{game_id}"),
        )
    else:
        kb.add(types.InlineKeyboardButton("📥 YUKLAB OLISH", callback_data=f"download_{game_id}"))
    return kb


# ============================================================
#                   MAJBURIY OBUNA TEKSHIRISH
# ============================================================

def check_subscription(user_id):
    conn = db()
    channels = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    if not channels:
        return True
    for ch in channels:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            # kanal ID noto'g'ri yoki bot admin emas — bloklamaslik uchun o'tkazib yuboramiz
            continue
    return True


def send_game_card(chat_id, game, admin_view=False):
    text = (f"🎮 <b>{game['name']}</b>\n\n"
            f"📝 {game['description'] or '-'}\n"
            f"📱 Versiya: {game['version'] or '-'}\n"
            f"📦 Hajmi: {game['size'] or '-'}\n"
            f"🗂 Kategoriya: {game['category'] or '-'}\n")
    if game["extra_info"]:
        text += f"ℹ️ {game['extra_info']}\n"
    if admin_view:
        text += f"\n🔑 Kod: <code>{game['code']}</code>\n📥 Yuklab olishlar: {game['downloads']}"

    kb = game_detail_kb(game["id"], admin_view=admin_view)
    if game["image_file_id"]:
        bot.send_photo(chat_id, game["image_file_id"], caption=text, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


# ============================================================
#                    /start VA KOD QIDIRISH (FOYDALANUVCHI)
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    touch_user(message.from_user)
    if get_setting("maintenance_mode") == "1" and not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🛠 Bot texnik ishlar tufayli vaqtincha ishlamayapti.")
        return
    text = get_setting("start_message").format(name=message.from_user.first_name or "")
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "👑 <b>ADMIN PANEL</b>\nBo'limni tanlang:", reply_markup=admin_main_menu())


# ============================================================
#              ASOSIY TEXT DISPATCHER (HAMMA MATNLAR)
# ============================================================

@bot.message_handler(content_types=["text"])
def text_dispatcher(message):
    uid = message.from_user.id
    touch_user(message.from_user)
    text = message.text.strip()

    # 1) Faol wizard bo'lsa — shunga yo'naltirish
    if uid in WIZ:
        if text == "❌ Bekor qilish":
            WIZ.pop(uid, None)
            bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=admin_main_menu())
            return
        handle_wizard_text(message)
        return

    # 2) Admin menyu tugmalari
    if is_admin(uid) and handle_admin_menu(message):
        return

    # 3) Maintenance mode (oddiy foydalanuvchi uchun)
    if get_setting("maintenance_mode") == "1" and not is_admin(uid):
        bot.send_message(message.chat.id, "🛠 Bot texnik ishlar tufayli vaqtincha ishlamayapti.")
        return

    # 4) Aks holda — bu kod qidiruvi deb hisoblanadi
    handle_code_lookup(message)


def handle_code_lookup(message):
    code = message.text.strip()
    conn = db()
    game = conn.execute("SELECT * FROM games WHERE code=?", (code,)).fetchone()
    conn.close()

    if not game:
        bot.send_message(message.chat.id, get_setting("not_found_message"))
        return

    if not check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, get_setting("force_sub_message"),
                          reply_markup=channels_inline_kb())
        WIZ[message.from_user.id] = {"flow": "pending_code", "data": {"code": code}}
        return

    send_game_card(message.chat.id, game, admin_view=False)


# ============================================================
#                       CALLBACK'LAR
# ============================================================

@bot.callback_query_handler(func=lambda c: True)
def callback_router(call):
    uid = call.from_user.id
    data = call.data

    if data == "checksub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
            pending = WIZ.pop(uid, None)
            if pending and pending.get("flow") == "pending_code":
                conn = db()
                game = conn.execute("SELECT * FROM games WHERE code=?",
                                     (pending["data"]["code"],)).fetchone()
                conn.close()
                if game:
                    send_game_card(call.message.chat.id, game, admin_view=False)
            else:
                bot.send_message(call.message.chat.id, "Endi o'yin kodini yuboring.")
        else:
            bot.answer_callback_query(call.id, "❌ Hali obuna bo'lmagansiz!", show_alert=True)
        return

    if data.startswith("download_"):
        game_id = int(data.split("_")[1])
        if not check_subscription(uid):
            bot.answer_callback_query(call.id, "❌ Avval kanallarga obuna bo'ling!", show_alert=True)
            return
        conn = db()
        game = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        if game and game["apk_file_id"]:
            bot.answer_callback_query(call.id, "⏳ Yuborilmoqda...")
            bot.send_document(call.message.chat.id, game["apk_file_id"],
                               caption=f"📥 {game['name']} — o'rnatishdan oldin \"noma'lum manbalar\"ga ruxsat bering.")
            conn.execute("UPDATE games SET downloads = downloads + 1 WHERE id=?", (game_id,))
            urow = conn.execute("SELECT id FROM users WHERE telegram_id=?", (uid,)).fetchone()
            conn.execute("INSERT INTO downloads (user_id, game_id, downloaded_at) VALUES (?, ?, ?)",
                         (urow["id"] if urow else None, game_id, now()))
            conn.commit()
        else:
            bot.answer_callback_query(call.id, "❌ Fayl topilmadi.", show_alert=True)
        conn.close()
        return

    # --- Quyidagi callback'lar faqat adminlar uchun ---
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "Ruxsat yo'q.")
        return

    if data.startswith("gamespage_"):
        page = int(data.split("_")[1])
        render_games_list(call.message.chat.id, page, edit_message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("gameopen_"):
        game_id = int(data.split("_")[1])
        conn = db()
        game = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        conn.close()
        if game:
            send_game_card(call.message.chat.id, game, admin_view=True)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("editmenu_"):
        game_id = int(data.split("_")[1])
        kb = types.InlineKeyboardMarkup(row_width=2)
        for field, label in EDIT_FIELD_LABELS.items():
            kb.add(types.InlineKeyboardButton(label, callback_data=f"editfield_{field}_{game_id}"))
        kb.add(types.InlineKeyboardButton("🖼 Rasmni almashtirish", callback_data=f"editimage_{game_id}"))
        bot.send_message(call.message.chat.id, "Qaysi maydonni tahrirlaysiz?", reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("editfield_"):
        _, field, game_id = data.split("_")
        WIZ[uid] = {"flow": "edit_field", "field": field, "game_id": int(game_id)}
        bot.send_message(call.message.chat.id, f"Yangi qiymatni kiriting ({EDIT_FIELD_LABELS[field]}):",
                          reply_markup=cancel_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("editimage_"):
        game_id = int(data.split("_")[1])
        WIZ[uid] = {"flow": "edit_image", "game_id": game_id}
        bot.send_message(call.message.chat.id, "Yangi rasmni yuboring:", reply_markup=cancel_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("replaceapk_"):
        game_id = int(data.split("_")[1])
        WIZ[uid] = {"flow": "replace_apk", "game_id": game_id}
        bot.send_message(call.message.chat.id, "Yangi APK faylni yuboring:", reply_markup=cancel_kb())
        bot.answer_callback_query(call.id)
        return

    if data.startswith("gamestat_"):
        game_id = int(data.split("_")[1])
        conn = db()
        game = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        total = conn.execute("SELECT COUNT(*) c FROM downloads WHERE game_id=?", (game_id,)).fetchone()["c"]
        conn.close()
        bot.send_message(call.message.chat.id,
                          f"📊 <b>{game['name']}</b>\n🔑 Kod: {game['code']}\n📥 Jami yuklab olishlar: {total}")
        bot.answer_callback_query(call.id)
        return

    if data.startswith("delconfirm_"):
        game_id = int(data.split("_")[1])
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"delyes_{game_id}"),
               types.InlineKeyboardButton("❌ Yo'q", callback_data="delno"))
        bot.send_message(call.message.chat.id, "Rostdan ham o'chirmoqchimisiz?", reply_markup=kb)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("delyes_"):
        game_id = int(data.split("_")[1])
        conn = db()
        g = conn.execute("SELECT name FROM games WHERE id=?", (game_id,)).fetchone()
        conn.execute("DELETE FROM games WHERE id=?", (game_id,))
        conn.execute("DELETE FROM downloads WHERE game_id=?", (game_id,))
        conn.commit()
        conn.close()
        log_action(uid, "O'yin o'chirildi", g["name"] if g else str(game_id))
        bot.send_message(call.message.chat.id, "🗑 O'chirildi.")
        bot.answer_callback_query(call.id)
        return

    if data == "delno":
        bot.answer_callback_query(call.id, "Bekor qilindi.")
        return

    if data.startswith("chandel_"):
        ch_id = int(data.split("_")[1])
        conn = db()
        conn.execute("DELETE FROM channels WHERE id=?", (ch_id,))
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id, "🗑 Kanal o'chirildi.")
        bot.answer_callback_query(call.id)
        return

    if data.startswith("admindel_"):
        tg_id = int(data.split("_")[1])
        if not is_main_admin(uid):
            bot.answer_callback_query(call.id, "Faqat asosiy admin o'chira oladi.", show_alert=True)
            return
        conn = db()
        conn.execute("DELETE FROM admins WHERE telegram_id=?", (tg_id,))
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id, "🗑 Admin o'chirildi.")
        bot.answer_callback_query(call.id)
        return


# ============================================================
#                     ADMIN MENYU TUGMALARI
# ============================================================

def handle_admin_menu(message):
    text = message.text
    chat_id = message.chat.id
    uid = message.from_user.id

    if text == "⬅️ Chiqish":
        bot.send_message(chat_id, "Admin panel yopildi.", reply_markup=types.ReplyKeyboardRemove())
        return True

    if text == "➕ O'yin qo'shish":
        WIZ[uid] = {"flow": "add_game", "step": 0, "data": {}}
        bot.send_message(chat_id, ADD_GAME_STEPS[0][1], reply_markup=cancel_kb())
        return True

    if text == "📋 O'yinlar":
        render_games_list(chat_id, page=0)
        return True

    if text == "🔑 Kodlar":
        conn = db()
        rows = conn.execute("SELECT code, name FROM games ORDER BY name").fetchall()
        conn.close()
        if not rows:
            bot.send_message(chat_id, "Hozircha kodlar yo'q.")
        else:
            lines = ["🔑 <b>Kodlar ro'yxati:</b>"] + [f"<code>{r['code']}</code> → {r['name']}" for r in rows]
      

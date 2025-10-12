import json
import os
import logging
import re
from threading import Thread
from flask import Flask

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ContextTypes, MessageHandler, filters,
                          PreCheckoutQueryHandler)

logging.basicConfig(level=logging.INFO)

# --------------------- ВСТАВЬ СЮДА СВОИ ДАННЫЕ (ты уже прислал) ---------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
STATES_FILE = "states.json"

# ссылки на каналы/пакеты
MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"     # обычный приват
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"  # VIP

# Кошельки/ссылки
USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
DONATALERTS_LINK = "https://www.donationalerts.com/r/gromn"  # если нужна отдельная — замени
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

# Провайдер звёзд (invoice)
STARS_PROVIDER_TOKEN = "STARS"
# --------------------------------------------------------------------

# In-memory structures (kept in sync with states.json)
# pending_users: {user_id: { 'state': 'awaiting_screenshot'|'support', 'pack': '<pack>', 'method': '<method>' }}
pending_users = {}
# admin_reply_state: {admin_id: user_id_to_reply}
admin_reply_state = {}

# -------------------- states.json handling --------------------
def load_states():
    global pending_users, admin_reply_state
    if not os.path.exists(STATES_FILE):
        pending_users = {}
        admin_reply_state = {}
        return
    try:
        with open(STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            pending_users = {int(k): v for k, v in data.get("pending_users", {}).items()}
            admin_reply_state = {int(k): v for k, v in data.get("admin_reply_state", {}).items()}
    except Exception as e:
        logging.exception("Не удалось загрузить states.json: %s", e)
        pending_users = {}
        admin_reply_state = {}

def save_states():
    try:
        tmp = STATES_FILE + ".tmp"
        data = {
            "pending_users": {str(k): v for k, v in pending_users.items()},
            "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()}
        }
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATES_FILE)
    except Exception as e:
        logging.exception("Не удалось сохранить states.json: %s", e)

# сразу подгружаем состояния при старте
load_states()

# ================== FLASK keep-alive ==================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ================== КЛАВИАТУРЫ ==================
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📦 Private", callback_data="menu_private")],
        [InlineKeyboardButton("👑 VIP Private", callback_data="menu_vip")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])

def duration_keyboard(prefix: str):
    # prefix: "private" or "vip"
    keyboard = [
        [InlineKeyboardButton("Месяц", callback_data=f"{prefix}_month")],
        [InlineKeyboardButton("Год", callback_data=f"{prefix}_year")],
        [InlineKeyboardButton("Навсегда", callback_data=f"{prefix}_forever")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_methods_keyboard(prefix_pack: str):
    # show payment methods after chosen pack (prefix_pack like "private_month" or "vip_year")
    keyboard = [
        [InlineKeyboardButton("⭐ Звёзды", callback_data=f"{prefix_pack}_stars")],
        [InlineKeyboardButton("💎 TON", callback_data=f"{prefix_pack}_ton")],
        [InlineKeyboardButton("💵 USDT", callback_data=f"{prefix_pack}_usdt")],
        [InlineKeyboardButton("🤖 CryptoBot", callback_data=f"{prefix_pack}_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины/России/Казахстана и других", callback_data=f"{prefix_pack}_countries")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def usdt_network_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("USDT TRC20", callback_data=f"{prefix_pack}_usdt_trc")],
        [InlineKeyboardButton("USDT ERC20", callback_data=f"{prefix_pack}_usdt_erc")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def countries_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix_pack}_country_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix_pack}_country_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан и другие", callback_data=f"{prefix_pack}_country_kaz_others")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def ukraine_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("Donatello", callback_data=f"{prefix_pack}_uk_donatello")],
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix_pack}_uk_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def russia_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix_pack}_ru_donatalerts")],
        [InlineKeyboardButton("FK Wallet", callback_data=f"{prefix_pack}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def kazakh_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix_pack}_kz_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================== HELPERS ==================
def pack_is_vip(pack: str) -> bool:
    return pack.startswith("vip_")

def get_channel_link_for_pack(pack: str) -> str:
    # VIP -> VIP_CHANNEL_LINK, else normal -> CHANNEL_LINK
    if pack_is_vip(pack):
        return VIP_CHANNEL_LINK
    return CHANNEL_LINK

# star amounts mapping
STARS_PRICES = {
    # pack_base: {duration: stars}
    "private": {"month": 200, "year": 500, "forever": 1000},
    "vip": {"month": 500, "year": 800, "forever": 1200},
}

# usd prices mapping
USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}

# ================== СТАРТ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # send photo with main channel and main keyboard
    if update.message:
        await update.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
            reply_markup=main_keyboard())
    elif update.callback_query:
        q = update.callback_query
        await q.message.reply_photo(photo=IMAGE_URL,
                                    caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
                                    reply_markup=main_keyboard())

# ================== ОБРАБОТКА КНОПОК ==================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    data = query.data

    # back to main
    if data == "back":
        await query.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
            reply_markup=main_keyboard())
        return

    # support
    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await query.message.reply_text("🛠 Напишите своё сообщение/пришлите скрин игры. Мы перешлём его модератору.")
        return

    # main menus
    if data == "menu_private":
        await query.message.reply_text("📦 Private — выберите срок:", reply_markup=duration_keyboard("private"))
        return
    if data == "menu_vip":
        await query.message.reply_text("👑 VIP Private — выберите срок:", reply_markup=duration_keyboard("vip"))
        return

    # durations -> show payment methods
    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        # show payment methods
        # show price summary
        usd = USD_PRICES[base][

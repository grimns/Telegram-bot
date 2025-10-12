import json
import os
import logging
import re
from threading import Thread
from flask import Flask

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)

# --- ТВОИ ДАННЫЕ ---
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"  
ADMIN_ID = 1758979923
STATES_FILE = "states.json"

MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATELLO_LINK = "https://donatello.to/Gromn"
DONATALERTS_LINK = "https://www.donationalerts.com/r/gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

# --- ЦЕНЫ ---
USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}

# --- СТАН ---
pending_users = {}
admin_reply_state = {}

# --- Работа с состояниями ---
def load_states():
    global pending_users, admin_reply_state
    if os.path.exists(STATES_FILE):
        try:
            with open(STATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                pending_users = {int(k): v for k, v in data.get("pending_users", {}).items()}
                admin_reply_state = {int(k): v for k, v in data.get("admin_reply_state", {}).items()}
        except Exception as e:
            logging.exception("Ошибка загрузки states.json: %s", e)

def save_states():
    try:
        data = {
            "pending_users": {str(k): v for k, v in pending_users.items()},
            "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()},
        }
        with open(STATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.exception("Ошибка сохранения states.json: %s", e)

load_states()

# --- Flask keep-alive ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run(): app.run(host='0.0.0.0', port=3000)
def keep_alive(): Thread(target=run, daemon=True).start()

# --- Клавиатуры ---
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Private", callback_data="menu_private")],
        [InlineKeyboardButton("👑 VIP Private", callback_data="menu_vip")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")],
    ])

def duration_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Месяц", callback_data=f"{prefix}_month")],
        [InlineKeyboardButton("Год", callback_data=f"{prefix}_year")],
        [InlineKeyboardButton("Навсегда", callback_data=f"{prefix}_forever")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def payment_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Звёзды", callback_data=f"{prefix_pack}_stars")],
        [InlineKeyboardButton("💎 TON", callback_data=f"{prefix_pack}_ton")],
        [InlineKeyboardButton("💵 USDT", callback_data=f"{prefix_pack}_usdt")],
        [InlineKeyboardButton("🤖 CryptoBot", callback_data=f"{prefix_pack}_cryptobot")],
        [InlineKeyboardButton("🌍 Украина / Россия / Казахстан", callback_data=f"{prefix_pack}_countries")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def usdt_network_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("USDT (TRC20)", callback_data=f"{prefix_pack}_usdt_trc")],
        [InlineKeyboardButton("USDT (ERC20)", callback_data=f"{prefix_pack}_usdt_erc")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def countries_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix_pack}_country_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix_pack}_country_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан", callback_data=f"{prefix_pack}_country_kazakhstan")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def russia_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix_pack}_ru_donatalerts")],
        [InlineKeyboardButton("FK Wallet", callback_data=f"{prefix_pack}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix_pack}_countries")]
    ])

# --- Утилиты ---
def get_channel_link(pack):
    return VIP_CHANNEL_LINK if pack.startswith("vip_") else CHANNEL_LINK

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}", reply_markup=main_keyboard())

# --- Основная логика ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Назад
    if data == "back":
        await query.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}", reply_markup=main_keyboard())
        return

    # Поддержка
    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await query.message.reply_text("🛠 Напишите сообщение или скиньте скрин игры — модератор ответит.")
        return

    # Меню
    if data == "menu_private":
        await query.message.reply_text("📦 Private — выберите срок:", reply_markup=duration_keyboard("private"))
        return
    if data == "menu_vip":
        await query.message.reply_text("👑 VIP Private — выберите срок:", reply_markup=duration_keyboard("vip"))
        return

    # Срок -> оплата
    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.groups()
        prefix_pack = f"{base}_{dur}"
        usd = USD_PRICES[base][dur]
        await query.message.reply_text(f"💰 Цена: {usd}$\nВыберите способ оплаты:", reply_markup=payment_methods_keyboard(prefix_pack))
        return

    # --- USDT ---
    if data.endswith("_usdt"):
        await query.message.reply_text("💵 Выберите сеть USDT:", reply_markup=usdt_network_keyboard(data))
        return
    if data.endswith("_usdt_trc"):
        await query.message.reply_text(f"💵 Отправьте USDT (TRC20): `{USDT_TRC20}`", parse_mode="Markdown")
        return
    if data.endswith("_usdt_erc"):
        await query.message.reply_text(f"💵 Отправьте USDT (ERC20): `{USDT_ERC20}`", parse_mode="Markdown")
        return

    # --- TON ---
    if data.endswith("_ton"):
        await query.message.reply_text(f"💎 Адрес TON: `{TON_ADDRESS}`", parse_mode="Markdown")
        return

    # --- CryptoBot ---
    if data.endswith("_cryptobot"):
        await query.message.reply_text(f"🤖 Оплата через CryptoBot:\n{CRYPTOBOT_LINK}")
        return

    # --- Украина / Россия / Казахстан ---
    if data.endswith("_countries"):
        await query.message.reply_text("🌍 Выберите страну:", reply_markup=countries_keyboard(data))
        return

    if data.endswith("_country_russia"):
        await query.message.reply_text("🇷🇺 Выберите способ оплаты:", reply_markup=russia_methods_keyboard(data))
        return

    # --- FK Wallet ---
    if data.endswith("_ru_fkwallet"):
        text = (
            "💳 Оплата через FK Wallet\n\n"
            f"1️⃣ Перейдите по ссылке: {FKWALLET_LINK}\n"
            "2️⃣ Войдите в кабинет\n"
            "3️⃣ Откройте: «Кошелёк» → «Рубли» → «Вывод»\n"
            f"4️⃣ Вставьте номер: `{FKWALLET_NUMBER}`\n"
            "5️⃣ Укажите сумму и подтвердите.\n\n"
            "После этого нажмите «Я оплатил» и отправьте скрин оплаты/чека — модератор проверит в течение 2 часов."
        )
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_confirm")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"{data}_country_russia")]
        ]))
        return

# --- Сообщения ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        await context.bot.send_message(
            ADMIN_ID,
            f"📩 Сообщение от @{update.message.from_user.username or 'без ника'} ({user_id}):\n{update.message.text or ''}"
        )
        await update.message.reply_text("✅ Ваше сообщение отправлено модератору.")
        pending_users.pop(user_id, None)
        save_states()

# --- Запуск ---
def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()

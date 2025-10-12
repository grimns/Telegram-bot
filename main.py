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

# === НАСТРОЙКИ ===
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
STATES_FILE = "states.json"

MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR4gkkE5jJb9D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"
STARS_PROVIDER_TOKEN = "STARS"  # вставишь свой

# === ЦЕНЫ ===
USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}
STAR_PRICES = {
    "private": {"month": 200, "year": 500, "forever": 1000},
    "vip": {"month": 500, "year": 800, "forever": 1200},
}

# === СОСТОЯНИЯ ===
pending_users = {}
admin_reply_state = {}

def load_states():
    global pending_users, admin_reply_state
    if os.path.exists(STATES_FILE):
        with open(STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            pending_users = {int(k): v for k, v in data.get("pending_users", {}).items()}
            admin_reply_state = {int(k): v for k, v in data.get("admin_reply_state", {}).items()}

def save_states():
    with open(STATES_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "pending_users": {str(k): v for k, v in pending_users.items()},
            "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()}
        }, f, ensure_ascii=False, indent=2)

load_states()

# === FLASK KEEP ALIVE ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    Thread(target=run, daemon=True).start()

# === КЛАВИАТУРЫ ===
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Private", callback_data="menu_private")],
        [InlineKeyboardButton("👑 VIP Private", callback_data="menu_vip")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")]
    ])

def duration_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Месяц", callback_data=f"{prefix}_month")],
        [InlineKeyboardButton("Год", callback_data=f"{prefix}_year")],
        [InlineKeyboardButton("Навсегда", callback_data=f"{prefix}_forever")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def payment_methods_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Звёзды", callback_data=f"{prefix}_stars")],
        [InlineKeyboardButton("💎 TON", callback_data=f"{prefix}_ton")],
        [InlineKeyboardButton("💵 USDT", callback_data=f"{prefix}_usdt")],
        [InlineKeyboardButton("🤖 CryptoBot", callback_data=f"{prefix}_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины / России / Казахстана", callback_data=f"{prefix}_countries")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def usdt_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("USDT TRC20", callback_data=f"{prefix}_usdt_trc")],
        [InlineKeyboardButton("USDT ERC20", callback_data=f"{prefix}_usdt_erc")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def countries_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix}_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix}_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан и другие", callback_data=f"{prefix}_kazakhstan")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def ru_methods_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix}_ru_donatalerts")],
        [InlineKeyboardButton("FK Wallet", callback_data=f"{prefix}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def ua_methods_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donatello", callback_data=f"{prefix}_uk_donatello")],
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix}_uk_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def kz_methods_keyboard(prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donat Alerts", callback_data=f"{prefix}_kz_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# === УТИЛИТЫ ===
def get_link_for_pack(pack):
    return VIP_CHANNEL_LINK if pack.startswith("vip_") else CHANNEL_LINK

# === СТАРТ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:",
        reply_markup=main_keyboard()
    )

# === КНОПКИ ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back":
        await query.message.reply_photo(photo=IMAGE_URL, caption="📢 Наш основной канал:", reply_markup=main_keyboard())
        return

    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await query.message.reply_text("🛠 Отправьте ваше сообщение или скрин оплаты/чек — модератор ответит вам в течение 2 часов.")
        return

    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        prefix = f"{m.group(1)}_{m.group(2)}"
        await query.message.reply_text("💰 Выберите способ оплаты:", reply_markup=payment_methods_keyboard(prefix))
        return

    # ========== ОПЛАТЫ ==========
    # Stars
    m = re.match(r"^(private|vip)_(month|year|forever)_stars$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        amount = STAR_PRICES[base][dur]
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{base.capitalize()} ({dur})",
            description="Покупка приват-доступа",
            payload=f"{base}_{dur}_stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=[LabeledPrice("Доступ", amount)],
        )
        return

    # TON
    m = re.match(r"^(private|vip)_(month|year|forever)_ton$", data)
    if m:
        await query.message.reply_text(f"💎 Оплата TON:\nОтправьте оплату на адрес:\n`{TON_ADDRESS}`\nПосле оплаты нажмите «Я оплатил».",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]]),
                                       parse_mode="Markdown")
        return

    # USDT
    m = re.match(r"^(private|vip)_(month|year|forever)_usdt$", data)
    if m:
        await query.message.reply_text("💵 Выберите сеть для USDT:", reply_markup=usdt_keyboard(f"{m.group(1)}_{m.group(2)}"))
        return

    # CryptoBot
    m = re.match(r"^(private|vip)_(month|year|forever)_cryptobot$", data)
    if m:
        await query.message.reply_text(f"🤖 Оплата через CryptoBot:\nПерейдите по ссылке {CRYPTOBOT_LINK}\nПосле оплаты нажмите «Я оплатил».",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]]))
        return

    # Countries
    m = re.match(r"^(private|vip)_(month|year|forever)_countries$", data)
    if m:
        await query.message.reply_text("🌍 Выберите страну:", reply_markup=countries_keyboard(f"{m.group(1)}_{m.group(2)}"))
        return

    # Украина
    m = re.match(r"^(private|vip)_(month|year|forever)_ukraine$", data)
    if m:
        await query.message.reply_text("🇺🇦 Выберите способ оплаты:", reply_markup=ua_methods_keyboard(f"{m.group(1)}_{m.group(2)}"))
        return

    # Россия
    m = re.match(r"^(private|vip)_(month|year|forever)_russia$", data)
    if m:
        await query.message.reply_text("🇷🇺 Выберите способ оплаты:", reply_markup=ru_methods_keyboard(f"{m.group(1)}_{m.group(2)}"))
        return

    # Казахстан
    m = re.match(r"^(private|vip)_(month|year|forever)_kazakhstan$", data)
    if m:
        await query.message.reply_text("🇰🇿 Выберите способ оплаты:", reply_markup=kz_methods_keyboard(f"{m.group(1)}_{m.group(2)}"))
        return

    # FK Wallet (Россия)
    if data.endswith("_ru_fkwallet"):
        await query.message.reply_text(
            f"💳 Оплата через FK Wallet:\n"
            f"1️⃣ Перейдите по ссылке {FKWALLET_LINK}\n"
            f"2️⃣ Войдите в кабинет → Кошелёк → Рубли → Вывод\n"
            f"3️⃣ Введите номер кошелька: `{FKWALLET_NUMBER}`\n"
            f"4️⃣ Отправьте сумму и нажмите «✅ Я оплатил»",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]])
        )
        return

    # После "Я оплатил"
    if data == "paid":
        pending_users[user_id] = {"state": "awaiting_screenshot"}
        save_states()
        await query.message.reply_text("📸 Отправьте скрин оплаты/чек модератору — он проверит в течение 2 часов и выдаст вам ссылку.")
        return

# === СООБЩЕНИЯ ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_users:
        state = pending_users[user_id]["state"]
        if state == "support" or state == "awaiting_screenshot":
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 Сообщение от @{update.message.from_user.username or 'Без ника'} ({user_id}):"
            )
            if update.message.photo:
                await update.message.photo[-1].get_file().download_to_drive(f"screenshot_{user_id}.jpg")
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=open(f"screenshot_{user_id}.jpg", "rb"))
                os.remove(f"screenshot_{user_id}.jpg")
            else:
                await context.bot.send_message(chat_id=ADMIN_ID, text=update.message.text)
            await context.bot.send_message(chat_id=ADMIN_ID,
                                           text="Ответить пользователю:",
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{user_id}")]]))
            await update.message.reply_text("✅ Ваше сообщение отправлено модератору!")
            del pending_users[user_id]
            save_states()

# === АДМИН ОТВЕТ ===
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if admin_id != ADMIN_ID:
        return
    m = re.match(r"reply_(\d+)", query.data)
    if m:
        uid = int(m.group(1))
        admin_reply_state[admin_id] = uid
        save_states()
        await query.message.reply_text(f"💬 Напиши ответ пользователю {uid}:")
        return

async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.from_user.id
    if admin_id == ADMIN_ID and admin_id in admin_reply_state:
        uid = admin_reply_state[admin_id]
        await context.bot.send_message(chat_id=uid, text=f"💬 Поддержка: {update.message.text}")
        await update.message.reply_text("✅ Ответ отправлен пользователю.")
        del admin_reply_state[admin_id]
        save_states()

# === MAIN ===
def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CallbackQueryHandler(admin_reply, pattern="^reply_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_message))
    app.run_polling()

if __name__ == "__main__":
    main()

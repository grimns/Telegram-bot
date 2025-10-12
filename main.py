import json
import os
import logging
import re
from threading import Thread
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
)

logging.basicConfig(level=logging.INFO)

# -------------------- НАСТРОЙКИ --------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
STARS_PROVIDER_TOKEN = "STARS"

IMAGE_URL = "https://ibb.co/hxbvxM4L"
MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR4gkkE5jJb9D"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATELLO_LINK = "https://donatello.to/Gromn"
DONATALERTS_LINK = "https://www.donationalerts.com/r/gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

STATES_FILE = "states.json"
# ---------------------------------------------------

# ====== ЦЕНЫ ======
STARS_PRICES = {
    "private": {"month": 200, "year": 500, "forever": 1000},
    "vip": {"month": 500, "year": 800, "forever": 1200},
}
USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}

# ====== ПАМЯТЬ ======
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
    data = {
        "pending_users": {str(k): v for k, v in pending_users.items()},
        "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()}
    }
    with open(STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_states()

# ====== FLASK KEEP ALIVE ======
app = Flask('')
@app.route('/')
def home(): return "Bot is running"
def run(): app.run(host='0.0.0.0', port=3000)
def keep_alive(): Thread(target=run, daemon=True).start()

# ====== КЛАВИАТУРЫ ======
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

def payment_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Stars", callback_data=f"{prefix_pack}_stars")],
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
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix_pack}")]
    ])

def countries_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix_pack}_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix_pack}_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан", callback_data=f"{prefix_pack}_kazakhstan")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix_pack}")]
    ])

# ====== ЛОГИКА ======
def get_channel_link_for_pack(pack):
    return VIP_CHANNEL_LINK if pack.startswith("vip") else CHANNEL_LINK

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(IMAGE_URL,
        caption=f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:",
        reply_markup=main_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = q.from_user
    await q.answer()

    if data == "back":
        await q.message.reply_photo(IMAGE_URL,
            caption=f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:",
            reply_markup=main_keyboard())
        return

    if data == "support":
        pending_users[user.id] = {"state": "support"}
        save_states()
        await q.message.reply_text("🛠 Напишите сообщение или пришлите скрин игры, модератор проверит и ответит.")
        return

    if data == "menu_private":
        await q.message.reply_text("📦 Private — выберите срок:", reply_markup=duration_keyboard("private"))
        return
    if data == "menu_vip":
        await q.message.reply_text("👑 VIP Private — выберите срок:", reply_markup=duration_keyboard("vip"))
        return

    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        usd = USD_PRICES[base][dur]
        await q.message.reply_text(f"💳 Стоимость: {usd}$\nВыберите способ оплаты:", reply_markup=payment_methods_keyboard(f"{base}_{dur}"))
        return

    # Stars
    if data.endswith("_stars"):
        pack = data.replace("_stars", "")
        base, dur = pack.split("_")
        stars = STARS_PRICES[base][dur]
        await context.bot.send_invoice(
            chat_id=user.id,
            title="Оплата Stars",
            description="Покупка доступа",
            payload=f"{pack}_stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=[LabeledPrice("Покупка доступа", stars * 100)],
        )
        return

    # USDT
    if data.endswith("_usdt"):
        await q.message.reply_text("Выберите сеть USDT:", reply_markup=usdt_network_keyboard(data.replace("_usdt", "")))
        return
    if data.endswith("_usdt_trc"):
        await q.message.reply_text(f"💵 Отправьте 3$ USDT (TRC20)\nАдрес: `{USDT_TRC20}`\n\nПосле оплаты нажмите 'Я оплатил'.", parse_mode="Markdown")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return
    if data.endswith("_usdt_erc"):
        await q.message.reply_text(f"💵 Отправьте 3$ USDT (ERC20)\nАдрес: `{USDT_ERC20}`\n\nПосле оплаты нажмите 'Я оплатил'.", parse_mode="Markdown")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

    # TON
    if data.endswith("_ton"):
        await q.message.reply_text(f"💎 Отправьте 3$ в TON на адрес:\n`{TON_ADDRESS}`\n\nПосле оплаты нажмите 'Я оплатил'.", parse_mode="Markdown")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

    # CryptoBot
    if data.endswith("_cryptobot"):
        await q.message.reply_text(f"🤖 Оплатите через CryptoBot:\n[{CRYPTOBOT_LINK}]({CRYPTOBOT_LINK})", parse_mode="Markdown")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

    # Страны
    if data.endswith("_countries"):
        await q.message.reply_text("Выберите страну:", reply_markup=countries_keyboard(data.replace("_countries", "")))
        return

    # Украина
    if data.endswith("_ukraine"):
        await q.message.reply_text(f"🇺🇦 Украина\nОплата через Donatello или Donat Alerts:\n{DONATELLO_LINK}\n{DONATALERTS_LINK}\n\nСумма: 125₴ / 3$\nПосле оплаты нажмите 'Я оплатил'.")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

    # Россия
    if data.endswith("_russia"):
        await q.message.reply_text(
            f"🇷🇺 Россия\nСпособы оплаты:\n1️⃣ Donat Alerts — {DONATALERTS_LINK}\n"
            f"2️⃣ Через FK Wallet — [Перейдите по ссылке]({FKWALLET_LINK})\n"
            f"Зайдите в кабинет → Кошелёк → Рубли → Вывод\n"
            f"Введите номер: `{FKWALLET_NUMBER}` и сумму 280₽ / 3$\n\nПосле оплаты нажмите 'Я оплатил'.",
            parse_mode="Markdown")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

    # Казахстан
    if data.endswith("_kazakhstan"):
        await q.message.reply_text(f"🇰🇿 Казахстан\nОплата через Donat Alerts:\n{DONATALERTS_LINK}\nСумма: 3$\nПосле оплаты нажмите 'Я оплатил'.")
        pending_users[user.id] = {"state": "awaiting_screenshot"}
        save_states()
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if pending_users.get(user_id, {}).get("state") == "awaiting_screenshot":
        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(ADMIN_ID, photo=photo, caption=f"📸 Новый скрин от @{update.message.from_user.username or user_id}\nНажмите, чтобы ответить пользователю.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Выдать ссылку", callback_data=f"approve_{user_id}")]]))
        await update.message.reply_text("✅ Скрин отправлен модератору. Проверка до 2 часов.")
        del pending_users[user_id]
        save_states()

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    if data.startswith("approve_"):
        uid = int(data.split("_")[1])
        link = get_channel_link_for_pack("vip" if "vip" in data else "private")
        await context.bot.send_message(uid, f"✅ Проверка завершена!\nВот ваша ссылка на доступ:\n{link}")
        await q.message.reply_text("✅ Ссылка выдана пользователю.")
        return

async def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_button, pattern=r"^approve_"))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

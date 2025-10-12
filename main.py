import json
import os
import logging
import re
import asyncio
from threading import Thread
from flask import Flask
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Update, LabeledPrice, InputFile, Bot
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, PreCheckoutQueryHandler
)

# ---------------- НАСТРОЙКИ ----------------
logging.basicConfig(level=logging.INFO)

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

DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

STARS_PROVIDER_TOKEN = "STARS"

STARS_PRICES = {
    "private": {"month": 200, "year": 500, "forever": 1000},
    "vip": {"month": 500, "year": 800, "forever": 1200},
}

USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}

pending_users = {}
admin_reply_state = {}

# ---------------- STATES ----------------
def load_states():
    global pending_users, admin_reply_state
    if os.path.exists(STATES_FILE):
        with open(STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        pending_users = {int(k): v for k, v in data.get("pending_users", {}).items()}
        admin_reply_state = {int(k): v for k, v in data.get("admin_reply_state", {}).items()}
    else:
        pending_users.clear()
        admin_reply_state.clear()

def save_states():
    data = {
        "pending_users": {str(k): v for k, v in pending_users.items()},
        "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()}
    }
    with open(STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_states()

# ---------------- FLASK ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run(): app.run(host='0.0.0.0', port=3000)
def keep_alive():
    Thread(target=run, daemon=True).start()

# ---------------- КЛАВИАТУРЫ ----------------
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Private", callback_data="menu_private")],
        [InlineKeyboardButton("👑 VIP Private", callback_data="menu_vip")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")]
    ])

def back_keyboard(): 
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])

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
        [InlineKeyboardButton("🌍 Оплата для Украины/России/Казахстана", callback_data=f"{prefix_pack}_countries")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def countries_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix_pack}_country_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix_pack}_country_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан и другие", callback_data=f"{prefix_pack}_country_kaz")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def ukraine_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donatello", callback_data=f"{prefix_pack}_uk_donatello")],
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_uk_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def russia_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_ru_donatalerts")],
        [InlineKeyboardButton("FK Wallet", callback_data=f"{prefix_pack}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def kazakh_methods_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_kz_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# ---------------- HELPERS ----------------
def pack_is_vip(pack): return pack.startswith("vip_")
def get_channel_link(pack): return VIP_CHANNEL_LINK if pack_is_vip(pack) else CHANNEL_LINK

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}\n\nВыберите раздел:", reply_markup=main_keyboard())

# ---------------- BUTTON HANDLER ----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = query.from_user.id; data = query.data

    if data == "back":
        await query.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}", reply_markup=main_keyboard()); return

    if data == "support":
        pending_users[user_id] = {"state": "support"}; save_states()
        await query.message.reply_text("🛠 Напишите сообщение или пришлите чек, модератор ответит."); return

    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.groups(); prefix_pack = f"{base}_{dur}"
        usd = USD_PRICES[base][dur]
        await query.message.reply_text(f"💰 Стоимость: {usd}$\nВыберите способ оплаты:", reply_markup=payment_methods_keyboard(prefix_pack))
        return

    if "_countries" in data:
        await query.message.reply_text("🌍 Выберите страну:", reply_markup=countries_keyboard(data.replace("_countries", ""))); return

    if "_country_ukraine" in data:
        await query.message.reply_text("🇺🇦 Украина — выберите метод:", reply_markup=ukraine_methods_keyboard(data.replace("_country_ukraine", ""))); return

    if "_country_russia" in data:
        await query.message.reply_text("🇷🇺 Россия — выберите метод:", reply_markup=russia_methods_keyboard(data.replace("_country_russia", ""))); return

    if "_country_kaz" in data:
        await query.message.reply_text("🇰🇿 Казахстан — выберите метод:", reply_markup=kazakh_methods_keyboard(data.replace("_country_kaz", ""))); return

    if "_ru_fkwallet" in data:
        await query.message.reply_text(
            f"💳 Оплата через FK Wallet\n\n"
            f"1️⃣ Перейдите по ссылке: {FKWALLET_LINK}\n"
            f"2️⃣ Войдите → кошелёк → рубли → вывод\n"
            f"3️⃣ Вставьте этот номер: `{FKWALLET_NUMBER}`\n"
            f"4️⃣ Укажите сумму.\n\nПосле оплаты нажмите «Я оплатил».",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]])
        ); return

    if data == "paid":
        pending_users[user_id] = {"state": "awaiting_screenshot"}; save_states()
        await query.message.reply_text("📸 Скиньте чек. Модератор проверит и выдаст ссылку в течение 2 часов."); return

    if "_stars" in data:
        base, dur = re.match(r"^(private|vip)_(month|year|forever)_stars$", data).groups()
        price = STARS_PRICES[base][dur]
        title = f"{base.capitalize()} {dur}"
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"Покупка {title}",
            description=f"Подписка {base} на {dur}",
            payload=f"{base}_{dur}_stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=[LabeledPrice(label=f"{title}", amount=price * 100)]
        ); return

# ---------------- ПРЕЧЕКАУТ ----------------
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload
    pack = payload.replace("_stars", "")
    link = get_channel_link(pack)
    await update.message.reply_text(f"✅ Оплата прошла успешно!\n\n🔗 Ваша ссылка: {link}")

# ---------------- СООБЩЕНИЯ ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_users:
        state = pending_users[user_id]["state"]
        if state == "awaiting_screenshot":
            await context.bot.send_message(ADMIN_ID, f"📩 Скрин от {user_id}")
            if update.message.photo:
                await update.message.photo[-1].get_file().download_to_drive("user_screenshot.jpg")
                await context.bot.send_photo(ADMIN_ID, photo=InputFile("user_screenshot.jpg"),
                                             caption=f"🧾 Проверить оплату пользователя {user_id}",
                                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Выдать ссылку", callback_data=f"give_{user_id}")]]))
            await update.message.reply_text("✅ Отправлено модератору. Проверка до 2 часов.")
            del pending_users[user_id]; save_states(); return

        if state == "support":
            await context.bot.send_message(ADMIN_ID, f"🛠 Сообщение от {user_id}: {update.message.text}")
            await update.message.reply_text("📩 Отправлено модератору."); return

# ---------------- ВЫДАТЬ ССЫЛКУ ----------------
async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    m = re.match(r"^give_(\d+)$", q.data)
    if m:
        uid = int(m.group(1))
        await context.bot.send_message(uid, "✅ Модератор подтвердил оплату!\n🔗 Ваша ссылка: " + get_channel_link("private"))
        await q.message.reply_text(f"Ссылка выдана пользователю {uid}")

# ---------------- MAIN ----------------
def main():
    keep_alive()

    # 🔧 Удаляем webhook перед запуском polling (исправляет ошибку Conflict)
    asyncio.run(Bot(TOKEN).delete_webhook(drop_pending_updates=True))

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CallbackQueryHandler(admin_button, pattern=r"^give_"))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()

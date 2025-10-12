import json
import os
import logging
import re
from threading import Thread
from flask import Flask
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters, PreCheckoutQueryHandler
)

# ---------------- НАСТРОЙКИ ----------------
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
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"
IMAGE_URL = "https://ibb.co/hxbvxM4L"

STARS_PROVIDER_TOKEN = "STARS"

logging.basicConfig(level=logging.INFO)

# ---------------- ПАМЯТЬ ----------------
pending_users = {}
admin_reply_state = {}

def load_states():
    global pending_users, admin_reply_state
    if os.path.exists(STATES_FILE):
        try:
            with open(STATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            pending_users = {int(k): v for k, v in data.get("pending_users", {}).items()}
            admin_reply_state = {int(k): v for k, v in data.get("admin_reply_state", {}).items()}
        except:
            pass

def save_states():
    data = {
        "pending_users": {str(k): v for k, v in pending_users.items()},
        "admin_reply_state": {str(k): v for k, v in admin_reply_state.items()},
    }
    with open(STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_states()

# ---------------- KEEP ALIVE ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=3000)

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
        [InlineKeyboardButton("💳 FK Wallet", callback_data=f"{prefix_pack}_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def usdt_network_keyboard(prefix_pack):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("USDT TRC20", callback_data=f"{prefix_pack}_usdt_trc")],
        [InlineKeyboardButton("USDT ERC20", callback_data=f"{prefix_pack}_usdt_erc")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# ---------------- ЦЕНЫ ----------------
USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}

UAH_RATE = 41.5
RUB_RATE = 95

def price_text(base, dur):
    usd = USD_PRICES[base][dur]
    uah = round(usd * UAH_RATE)
    rub = round(usd * RUB_RATE)
    return f"{uah}₴ / {rub}₽ / ${usd}"

def get_channel_link_for_pack(pack):
    return VIP_CHANNEL_LINK if pack.startswith("vip") else CHANNEL_LINK

# ---------------- ОБРАБОТКА ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(photo=IMAGE_URL,
        caption=f"📢 Наш канал: {MAIN_CHANNEL}\n\nВыберите раздел:",
        reply_markup=main_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data

    if data == "back":
        await q.message.reply_photo(photo=IMAGE_URL,
            caption=f"📢 Наш канал: {MAIN_CHANNEL}\n\nВыберите раздел:",
            reply_markup=main_keyboard())
        return

    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await q.message.reply_text("🛠 Напишите сообщение или отправьте скрин — модератор ответит.")
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
        price = price_text(base, dur)
        await q.message.reply_text(
            f"💳 Стоимость: {price}\n\nВыберите способ оплаты:",
            reply_markup=payment_methods_keyboard(f"{base}_{dur}"))
        return

    if data.endswith("_usdt"):
        await q.message.reply_text("Выберите сеть:", reply_markup=usdt_network_keyboard(data))
        return

    # USDT сети
    if "_usdt_trc" in data:
        await q.message.reply_text(f"💵 Отправьте оплату на адрес TRC20:\n`{USDT_TRC20}`", parse_mode="Markdown")
        await q.message.reply_text("После оплаты нажмите 'Я оплатил'", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_paid")]
        ]))
        return

    if "_usdt_erc" in data:
        await q.message.reply_text(f"💵 Отправьте оплату на адрес ERC20:\n`{USDT_ERC20}`", parse_mode="Markdown")
        await q.message.reply_text("После оплаты нажмите 'Я оплатил'", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_paid")]
        ]))
        return

    if "_fkwallet" in data:
        await q.message.reply_text(
            f"💳 Оплата через FK Wallet\n\n1️⃣ Перейдите по ссылке: {FKWALLET_LINK}\n"
            f"2️⃣ Войдите в кабинет.\n3️⃣ Выберите «Кошелёк» → «Рубли» → «Вывод».\n"
            f"4️⃣ Введите номер `{FKWALLET_NUMBER}` и сумму по вашему пакету.\n\nПосле оплаты нажмите 'Я оплатил'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_paid")]
            ])
        )
        return

    if "_cryptobot" in data:
        await q.message.reply_text(f"🤖 Оплата через CryptoBot:\n{CRYPTOBOT_LINK}")
        await q.message.reply_text("После оплаты нажмите 'Я оплатил'", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_paid")]
        ]))
        return

    if "_ton" in data:
        await q.message.reply_text(f"💎 Отправьте оплату на TON адрес:\n`{TON_ADDRESS}`", parse_mode="Markdown")
        await q.message.reply_text("После оплаты нажмите 'Я оплатил'", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"{data}_paid")]
        ]))
        return

    if "_stars" in data:
        base, dur = data.split("_")[:2]
        usd = USD_PRICES[base][dur]
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Покупка подписки",
            description=f"{base.capitalize()} — {dur}",
            payload=data,
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=[LabeledPrice("Подписка", usd * 100)]
        )
        return

    if data.endswith("_paid"):
        pending_users[user_id] = {"state": "awaiting_screenshot", "pack": data}
        save_states()
        await q.message.reply_text("✅ Отлично! Скиньте скрин оплаты/чек — модератор проверит в и выдаст ссылку течение 2 часов.")
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if pending_users.get(user_id, {}).get("state") == "awaiting_screenshot":
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_path = await file.download_to_drive()
        await context.bot.send_photo(
            ADMIN_ID, photo=open(file_path, "rb"),
            caption=f"📷 Скрин от @{update.message.from_user.username or user_id}\n"
                    f"Пакет: {pending_users[user_id]['pack']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Выдать ссылку", callback_data=f"give_{user_id}")]
            ])
        )
        await update.message.reply_text("✅ Скрин отправлен модератору. Ожидайте ответа в течение 2 часов.")
    elif pending_users.get(user_id, {}).get("state") == "support":
        await context.bot.forward_message(ADMIN_ID, user_id, update.message.message_id)

async def give_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = int(q.data.split("_")[1])
    pack = pending_users.get(user_id, {}).get("pack", "")
    link = get_channel_link_for_pack(pack)
    await context.bot.send_message(user_id, f"✅ Оплата подтверждена!\nВаша ссылка: {link}")
    await q.message.reply_text("Ссылка выдана ✅")
    pending_users.pop(user_id, None)
    save_states()

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    payload = update.message.successful_payment.invoice_payload
    link = get_channel_link_for_pack(payload)
    await update.message.reply_text(f"✅ Оплата получена! Ваша ссылка: {link}")

# ---------------- ЗАПУСК ----------------
def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CallbackQueryHandler(give_link, pattern=r"^give_"))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.run_polling()

if __name__ == "__main__":
    main()

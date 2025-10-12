# main.py — полный рабочий код (telegram.ext v20+)
import json
import os
import logging
import re
from threading import Thread
from flask import Flask

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    LabeledPrice
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    PreCheckoutQueryHandler
)

logging.basicConfig(level=logging.INFO)

# --------------------- НАСТРОЙКИ: вставь свои значения ---------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"   # <- твой токен
ADMIN_ID = 1758979923                                     # <- твой Telegram ID
STATES_FILE = "states.json"
STARS_PROVIDER_TOKEN = "STARS"  # <- вставишь свой провайдер (BotFather/invoice provider)
# --------------------------------------------------------------------------

# Ссылки, кошельки, картинки (оставлены те, что ты присылал)
MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
DONATALERTS_LINK = "https://www.donationalerts.com/r/gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

# ========== ЦЕНЫ ==========
STARS_PRICES = {
    "private": {"month": 200, "year": 500, "forever": 1000},
    "vip": {"month": 500, "year": 800, "forever": 1200},
}

USD_PRICES = {
    "private": {"month": 3, "year": 5, "forever": 10},
    "vip": {"month": 5, "year": 10, "forever": 15},
}
# ==========================

# В памяти + persist
pending_users = {}         # { user_id: {'state': 'awaiting_screenshot'|'support', 'pack': 'private_month', 'method': 'usdt_trc'} }
admin_reply_state = {}     # { admin_id: target_user_id }

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

load_states()

# ================== FLASK keep-alive (необязательно, но удобно для хостинга) ==================
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
    # prefix: private or vip
    keyboard = [
        [InlineKeyboardButton("Месяц", callback_data=f"{prefix}_month")],
        [InlineKeyboardButton("Год", callback_data=f"{prefix}_year")],
        [InlineKeyboardButton("Навсегда", callback_data=f"{prefix}_forever")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("⭐ Звёзды", callback_data=f"{prefix_pack}_stars")],
        [InlineKeyboardButton("💎 TON", callback_data=f"{prefix_pack}_ton")],
        [InlineKeyboardButton("💵 USDT", callback_data=f"{prefix_pack}_usdt")],
        [InlineKeyboardButton("🤖 CryptoBot", callback_data=f"{prefix_pack}_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины/России/Казахстана", callback_data=f"{prefix_pack}_countries")],
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
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_uk_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def russia_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_ru_donatalerts")],
        [InlineKeyboardButton("FK Wallet", callback_data=f"{prefix_pack}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def kazakh_methods_keyboard(prefix_pack: str):
    keyboard = [
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_kz_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================== HELPERS ==================
def pack_is_vip(pack: str) -> bool:
    return pack.startswith("vip_")

def get_channel_link_for_pack(pack: str) -> str:
    if pack_is_vip(pack):
        return VIP_CHANNEL_LINK
    return CHANNEL_LINK

def price_display(base, dur):
    usd = USD_PRICES[base][dur]
    conv = {3: {"uah": 125, "rub": 280}, 5: {"uah": 210, "rub": 470}, 10: {"uah": 420, "rub": 940}, 15: {"uah": 630, "rub": 1410}}
    vals = conv.get(usd, {"uah": int(usd*42), "rub": int(usd*93)})
    return f"{vals['uah']}₴ / {vals['rub']}₽ / ${usd}"

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # support both message and callback triggers
    if update.message:
        await update.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
            reply_markup=main_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
            reply_markup=main_keyboard()
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    username = user.username or f"id{user_id}"
    data = query.data

    # BACK
    if data == "back":
        await query.message.reply_photo(photo=IMAGE_URL,
                                        caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите раздел:"),
                                        reply_markup=main_keyboard())
        return

    # SUPPORT
    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await query.message.reply_text("🛠 Напишите своё сообщение/пришлите скрин игры. Мы перешлём его модератору.")
        return

    # MAIN MENUS
    if data == "menu_private":
        await query.message.reply_text("📦 Private — выберите срок:", reply_markup=duration_keyboard("private"))
        return
    if data == "menu_vip":
        await query.message.reply_text("👑 VIP Private — выберите срок:", reply_markup=duration_keyboard("vip"))
        return

    # DURATIONS -> show payment methods + price summary
    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        usd = USD_PRICES[base][dur]
        stars = STARS_PRICES[base][dur]
        await query.message.reply_text(
            f"Пакет: {base.title()} | Срок: {dur}\nЦена: {price_display(base,dur)} или {stars}⭐\nВыберите способ оплаты:",
            reply_markup=payment_methods_keyboard(prefix_pack))
        return

    # ========== STARS (invoice) ==========
    m = re.match(r"^(private|vip)_(month|year|forever)_stars$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        stars_amount = STARS_PRICES[base][dur]
        prices = [LabeledPrice("Звёзды", stars_amount)]
        payload = f"{base}_{dur}_stars"
        try:
            await query.message.reply_invoice(
                title=f"{base.title()} {dur} — Звёзды",
                description=f"Покупка {stars_amount}⭐ для {base} ({dur})",
                payload=payload,
                provider_token=STARS_PROVIDER_TOKEN,
                currency="XTR",
                prices=prices,
                start_parameter=f"{base}_{dur}_stars",
            )
        except Exception as e:
            logging.exception("Ошибка invoice: %s", e)
            await query.message.reply_text("❌ Не удалось создать инвойс. Проверь provider_token.")
        return

    # TON
    m = re.match(r"^(private|vip)_(month|year|forever)_ton$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_ton")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: {price_display(base,dur)}\nАдрес: `{TON_ADDRESS}`\n\nПосле перевода нажмите 'Я оплатил' и скиньте оплаты/чека.",
            parse_mode="Markdown",
            reply_markup=kb)
        return

    # USDT -> choose network
    m = re.match(r"^(private|vip)_(month|year|forever)_usdt$", data)
    if m:
        prefix_pack = f"{m.group(1)}_{m.group(2)}"
        await query.message.reply_text("💵 Выберите сеть для оплаты USDT:", reply_markup=usdt_network_keyboard(prefix_pack))
        return

    # USDT TRC
    m = re.match(r"^(private|vip)_(month|year|forever)_usdt_trc$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_usdt_trc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💵 Оплата USDT TRC20\nСумма: {price_display(base,dur)}\nАдрес TRC20: `{USDT_TRC20}`\n\nПосле оплаты нажмите 'Я оплатил' и скиньте оплаты/чека.",
            parse_mode="Markdown",
            reply_markup=kb)
        return

    # USDT ERC
    m = re.match(r"^(private|vip)_(month|year|forever)_usdt_erc$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_usdt_erc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💵 Оплата USDT ERC20\nСумма: {price_display(base,dur)}\nАдрес ERC20: `{USDT_ERC20}`\n\nПосле оплаты нажмите 'Я оплатил' и скиньте оплаты/чека.",
            parse_mode="Markdown",
            reply_markup=kb)
        return

    # CryptoBot
    m = re.match(r"^(private|vip)_(month|year|forever)_cryptobot$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в CryptoBot", url=f"https://{CRYPTOBOT_LINK}" if not CRYPTOBOT_LINK.startswith("http") else CRYPTOBOT_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_cryptobot")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nСумма: {price_display(base,dur)}\n\nПосле оплаты нажмите 'Я оплатил' и скиньте оплаты/чека.",
            reply_markup=kb)
        return

    # countries menu
    m = re.match(r"^(private|vip)_(month|year|forever)_countries$", data)
    if m:
        prefix_pack = f"{m.group(1)}_{m.group(2)}"
        await query.message.reply_text("Выберите страну оплаты:", reply_markup=countries_keyboard(prefix_pack))
        return

    # Ukraine -> Donatello
    m = re.match(r"^(private|vip)_(month|year|forever)_uk_donatello$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в Donatello", url=DONATELLO_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_uk_donatello")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💰 Donatello\nСумма: {price_display(base,dur)}\n\nНажмите кнопку, чтобы перейти на Donatello. После оплаты — 'Я оплатил' + оплаты/чека.",
            reply_markup=kb)
        return

    # Ukraine -> Donation Alerts
    m = re.match(r"^(private|vip)_(month|year|forever)_uk_donatalerts$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в DonationAlerts", url=DONATION_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_uk_donatalerts")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💰 Donation Alerts\nСумма: {price_display(base,dur)}\n\nНажмите кнопку, чтобы перейти. После оплаты — 'Я оплатил' + оплаты/чека.",
            reply_markup=kb)
        return

    # Russia -> Donation Alerts
    m = re.match(r"^(private|vip)_(month|year|forever)_ru_donatalerts$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в DonationAlerts", url=DONATALERTS_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_ru_donatalerts")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💰 Donation Alerts\nСумма: {price_display(base,dur)}\n\nНажмите кнопку, чтобы перейти. После оплаты — 'Я оплатил' + оплаты/чека.",
            reply_markup=kb)
        return

    # Russia -> FK Wallet (show URL + instructions + Я оплатил)
    if data.endswith("_ru_fkwallet"):
        parts = data.split("_")
        base, dur = parts[0], parts[1] if len(parts) > 1 else ("private", "month")
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в FK Wallet", url=FKWALLET_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_ru_fkwallet")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        instr = (f"💳 FK Wallet — инструкция\n\n"
                 f"1) Перейдите по ссылке: {FKWALLET_LINK}\n"
                 f"2) В кабинете: Кошелёк → Рубли → Вывод\n"
                 f"3) Вставьте номер: `{FKWALLET_NUMBER}`\n"
                 f"4) Укажите сумму: {price_display(base,dur)} и подтвердите перевод\n\n"
                 "После оплаты нажмите '✅ Я оплатил' и скиньте скрин оплаты/чека.")
        await query.message.reply_text(instr, parse_mode="Markdown", reply_markup=kb)
        return

    # Kazakhstan -> Donation Alerts
    m = re.match(r"^(private|vip)_(month|year|forever)_kz_donatalerts$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        prefix_pack = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в DonationAlerts", url=DONATALERTS_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix_pack}_kz_donatalerts")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        await query.message.reply_text(
            f"💰 Donation Alerts (Казахстан)\nСумма: {price_display(base,dur)}\n\nПосле оплаты нажмите 'Я оплатил' и пришлите скрин оплаты/чека.",
            reply_markup=kb)
        return

    # ====== Пользователь нажал "Я оплатил" (в любом варианте) ======
    if data.startswith("paid_") or data == "paid":
        payload = data.replace("paid_", "") if data.startswith("paid_") else ""
        parts = payload.split("_") if payload else []
        if len(parts) >= 2:
            pack = f"{parts[0]}_{parts[1]}"
            method = "_".join(parts[2:]) if len(parts) > 2 else "manual"
        else:
            pack = "unknown_unknown"
            method = "manual"
        pending_users[user_id] = {"state": "awaiting_screenshot", "pack": pack, "method": method}
        save_states()
        await query.message.reply_text("✅ Нажато: 'Я оплатил'. Пожалуйста, скиньте скрин оплаты/чека — модератор проверит и выдаст ссылку в течение 2 часов.")
        # notify admin
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"Пользователь @{username} (ID: {user_id}) отметил оплату: {pack} | способ: {method}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Выдать ссылку @{username}", callback_data=f"give_{user_id}")],
                                                  [InlineKeyboardButton(f"Ответить пользователю", callback_data=f"replyto_{user_id}")]])
            )
        except Exception as e:
            logging.exception("Не удалось уведомить админа о пометке оплаты: %s", e)
        return

    # admin: give link
    if data.startswith("give_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        try:
            target_id = int(data.split("_", 1)[1])
        except Exception:
            await query.answer("❌ Неверный идентификатор.", show_alert=True)
            return
        if target_id in pending_users:
            info = pending_users[target_id]
            pack = info.get("pack", "unknown_unknown")
            link = get_channel_link_for_pack(pack)
            try:
                await context.bot.send_message(target_id, f"✅ Оплата подтверждена! Вот ссылка на канал:\n{link}")
                await query.answer(f"Ссылка отправлена пользователю {target_id}")
                del pending_users[target_id]
                save_states()
            except Exception as e:
                logging.exception("Не удалось отправить ссылку пользователю: %s", e)
                await query.answer("❌ Не удалось отправить ссылку пользователю.", show_alert=True)
        else:
            await query.answer("Пользователь не найден в списке ожидающих оплат.", show_alert=True)
        return

    # admin: replyto_ (установить state для ответов)
    if data.startswith("replyto_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        try:
            uid = int(data.split("_", 1)[1])
            admin_reply_state[user_id] = uid
            save_states()
            await query.message.reply_text(f"✍️ Отправь сообщение — оно будет переслано пользователю {uid}.")
        except Exception:
            await query.answer("❌ Неверный идентификатор.", show_alert=True)
        return

    # Упавшие случаи — ничего не делаем
    await query.answer()

# ================== PreCheckout (для invoice) ==================
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# ================== Успешная оплата Stars (invoice) ==================
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    payload = payment.invoice_payload

    if payload and payload.endswith("_stars"):
        if "vip" in payload:
            link = VIP_CHANNEL_LINK
        else:
            link = CHANNEL_LINK
        try:
            await update.message.reply_text(f"✅ Оплата успешна! Вот ссылка на канал:\n{link}")
            await context.bot.send_message(ADMIN_ID, f"Пользователь @{update.message.from_user.username or user_id} (ID: {user_id}) оплатил (stars) {payload}")
        except Exception:
            pass

# ================== Обработка фото (скрин игры / support) ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or f"id{user_id}"

    if user_id in pending_users:
        state = pending_users[user_id].get("state")
        if state == "awaiting_screenshot":
            info = pending_users[user_id]
            pack = info.get("pack", "unknown")
            method = info.get("method", "unknown")
            caption_type = f"Пакет: {pack} | Метод: {method}\nID: {user_id}"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"Выдать ссылку @{username}", callback_data=f"give_{user_id}")],
                                             [InlineKeyboardButton("Ответить пользователю", callback_data=f"replyto_{user_id}")]])
            try:
                # пересылаем фото админу с подписью
                await context.bot.send_photo(
                    ADMIN_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=(f"📸 Скрин оплаты/чека от @{username} (ID: {user_id})\n{caption_type}"),
                    reply_markup=keyboard
                )
                await update.message.reply_text("📨 Скрин отправлен модератору, ожидайте проверки.")
            except Exception as e:
                logging.exception("Ошибка при пересылке скрина админу: %s", e)
                await update.message.reply_text("❌ Не удалось отправить скрин. Попробуйте позже.")
            return
        elif state == "support":
            try:
                await context.bot.send_photo(
                    ADMIN_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=(f"📸 Сообщение/скрин поддержки от @{username} (ID: {user_id})"),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить пользователю", callback_data=f"replyto_{user_id}")]])
                )
                await update.message.reply_text("📨 Ваше фото/сообщение отправлено в поддержку.")
            except Exception as e:
                logging.exception("Ошибка при отправке поддержки админу: %s", e)
                await update.message.reply_text("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
            try:
                del pending_users[user_id]
                save_states()
            except KeyError:
                pass
            return

    # пользователь прислал фото без пометки оплаты/поддержки
    await update.message.reply_text(
        "❗ Чтобы отправить скрин оплаты/чека для подтверждения доступа — сначала нажмите 'Я оплатил' в меню нужного пакета.\n"
        "Для поддержки нажмите кнопку '🛠 Поддержка'."
    )

# ================== Обработка текста (support & admin replies) ==================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or ""
    username = user.username or f"id{user_id}"

    # user -> support
    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📨 Сообщение поддержки от @{username} (ID: {user_id}):\n\n{text}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить пользователю", callback_data=f"replyto_{user_id}")]])
            )
            await update.message.reply_text("✅ Ваше сообщение отправлено. Ожидайте ответ.")
        except Exception as e:
            logging.exception("Ошибка при отправке поддержки админу: %s", e)
            await update.message.reply_text("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
        try:
            del pending_users[user_id]
            save_states()
        except KeyError:
            pass
        return

    # admin: stateful reply (after clicking replyto_ button)
    if user_id == ADMIN_ID and user_id in admin_reply_state:
        target_id = admin_reply_state[user_id]
        if not text.strip():
            await update.message.reply_text("❗ Напишите текст, чтобы отправить ответ пользователю.")
            return
        try:
            await context.bot.send_message(target_id, f"💬 Поддержка:\n\n{text}")
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
        try:
            del admin_reply_state[user_id]
            save_states()
        except KeyError:
            pass
        return

    # admin: reply via replying to admin-chat message (parse ID inside caption/text)
    if user_id == ADMIN_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message
        content = (orig.text or "") + "\n" + (orig.caption or "")
        m = re.search(r"ID[:\s]*([0-9]{5,})", content)
        if m:
            try:
                target = int(m.group(1))
                if not text.strip():
                    await update.message.reply_text("❗ Напишите текст, чтобы отправить ответ пользователю.")
                    return
                await context.bot.send_message(target, f"💬 Поддержка:\n\n{text}")
                await update.message.reply_text(f"✅ Ответ отправлен пользователю {target}")
            except Exception as e:
                await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
            return

    # admin: /reply_<id> command
    if text.startswith("/reply_") and user_id == ADMIN_ID:
        parts = text.split(" ", 1)
        cmd = parts[0]
        reply_text = parts[1] if len(parts) > 1 else ""
        if "_" in cmd and reply_text:
            try:
                target_id = int(cmd.replace("/reply_", ""))
                try:
                    await context.bot.send_message(target_id, f"💬 Поддержка:\n\n{reply_text}")
                    await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
                except Exception as e:
                    await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID. Используйте /reply_<id> текст")
        else:
            await update.message.reply_text("❌ Используйте формат: /reply_<id> текст")
        return

    # default hint to users
    await update.message.reply_text(
        "Если вы хотите оплатить — нажмите /start и выберите пакет. Для поддержки нажмите кнопку '🛠 Поддержка'."
    )

# ================== ЗАПУСК ==================
def main():
    load_states()
    keep_alive()

    if TOKEN.startswith("<") or ADMIN_ID == 0:
        print("ERROR: Вставь TOKEN и ADMIN_ID в начало файла перед запуском.")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

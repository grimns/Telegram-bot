# main_fixed_fkwallet.py
import json
import os
import logging
import re
from threading import Thread
from flask import Flask
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters,
    PreCheckoutQueryHandler
)

logging.basicConfig(level=logging.INFO)

# --------------------- ТВОИ ДАННЫЕ ---------------------
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

DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
DONATALERTS_LINK = "https://www.donationalerts.com/r/gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

STARS_PROVIDER_TOKEN = "provider.stars"

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

# ---------------- states persistence (unchanged) ----------------
def load_states():
    global pending_users, admin_reply_state
    if not os.path.exists(STATES_FILE):
        pending_users.clear()
        admin_reply_state.clear()
        return
    try:
        with open(STATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        pending_users.update({int(k): v for k, v in data.get("pending_users", {}).items()})
        admin_reply_state.update({int(k): v for k, v in data.get("admin_reply_state", {}).items()})
    except Exception as e:
        logging.exception("Не удалось загрузить states.json: %s", e)
        pending_users.clear()
        admin_reply_state.clear()

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

# ---------------- keep-alive ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    Thread(target=run, daemon=True).start()

# ---------------- keyboards ----------------
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Private", callback_data="menu_private")],
        [InlineKeyboardButton("👑 VIP Private", callback_data="menu_vip")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")],
    ])

def duration_keyboard(prefix: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Месяц", callback_data=f"{prefix}_month")],
        [InlineKeyboardButton("Год", callback_data=f"{prefix}_year")],
        [InlineKeyboardButton("Навсегда", callback_data=f"{prefix}_forever")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def payment_methods_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Звёзды", callback_data=f"{prefix_pack}_stars")],
        [InlineKeyboardButton("💎 TON", callback_data=f"{prefix_pack}_ton")],
        [InlineKeyboardButton("💵 USDT", callback_data=f"{prefix_pack}_usdt")],
        [InlineKeyboardButton("🤖 CryptoBot", callback_data=f"{prefix_pack}_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины/России/Казахстана", callback_data=f"{prefix_pack}_countries")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def usdt_network_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("USDT TRC20", callback_data=f"{prefix_pack}_usdt_trc")],
        [InlineKeyboardButton("USDT ERC20", callback_data=f"{prefix_pack}_usdt_erc")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def countries_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Украина", callback_data=f"{prefix_pack}_country_ukraine")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data=f"{prefix_pack}_country_russia")],
        [InlineKeyboardButton("🇰🇿 Казахстан", callback_data=f"{prefix_pack}_country_kaz")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def ukraine_methods_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donatello", callback_data=f"{prefix_pack}_uk_donatello")],
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_uk_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def russia_methods_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_ru_donatalerts")],
        # FK Wallet is shown as a URL button + separate "Я оплатил" button when choosing FK Wallet branch
        [InlineKeyboardButton("FK Wallet (внутри России)", callback_data=f"{prefix_pack}_ru_fkwallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def kazakh_methods_keyboard(prefix_pack: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donation Alerts", callback_data=f"{prefix_pack}_kz_donatalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# ---------------- helpers ----------------
def pack_is_vip(pack: str) -> bool:
    return pack.startswith("vip_")

def get_channel_link_for_pack(pack: str) -> str:
    return VIP_CHANNEL_LINK if pack_is_vip(pack) else CHANNEL_LINK

def price_display(base, dur):
    usd = USD_PRICES[base][dur]
    conv = {
        3: {"uah": 125, "rub": 280},
        5: {"uah": 210, "rub": 470},
        10: {"uah": 420, "rub": 940},
        15: {"uah": 630, "rub": 1410}
    }
    vals = conv.get(usd, {"uah": int(usd*42), "rub": int(usd*93)})
    return f"{vals['uah']}₴ / {vals['rub']}₽ / ${usd}"

# ---------------- handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}\n\nВыберите раздел:", reply_markup=main_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}\n\nВыберите раздел:", reply_markup=main_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    user_id = user.id
    username = user.username or f"id{user_id}"
    data = q.data

    if data == "back":
        await q.message.reply_photo(IMAGE_URL, caption=f"📢 Наш канал: {MAIN_CHANNEL}", reply_markup=main_keyboard())
        return

    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await q.message.reply_text("🛠 Напишите своё сообщение/пришлите скрин игры. Мы перешлём его модератору.")
        return

    # menu -> choose duration
    m = re.match(r"^(private|vip)_(month|year|forever)$", data)
    if m:
        base, dur = m.group(1), m.group(2)
        await q.message.reply_text(f"{base.title()} — {dur}\nЦена: {price_display(base,dur)}\nВыберите способ оплаты:", reply_markup=payment_methods_keyboard(f"{base}_{dur}"))
        return

    # countries menu
    if data.endswith("_countries"):
        prefix = data.replace("_countries", "")
        await q.message.reply_text("Выберите страну:", reply_markup=countries_keyboard(prefix))
        return

    # Ukraine/Russia/Kazakhstan branches
    if data.endswith("_country_ukraine"):
        prefix = data.replace("_country_ukraine", "")
        await q.message.reply_text("Способы оплаты (Украина):", reply_markup=ukraine_methods_keyboard(prefix))
        return
    if data.endswith("_country_russia"):
        prefix = data.replace("_country_russia", "")
        await q.message.reply_text("Способы оплаты (Россия):", reply_markup=russia_methods_keyboard(prefix))
        return
    if data.endswith("_country_kaz"):
        prefix = data.replace("_country_kaz", "")
        await q.message.reply_text("Способы оплаты (Казахстан):", reply_markup=kazakh_methods_keyboard(prefix))
        return

    # Ukraine -> Donatello
    if data.endswith("_uk_donatello"):
        base, dur = data.split("_")[:2]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в Donatello", url=DONATELLO_LINK)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_uk_donatello")]
        ])
        await q.message.reply_text(f"Donatello — Сумма: {price_display(base,dur)}\nСсылка нажмите ниже.", reply_markup=kb)
        return

    # Ukraine -> Donation Alerts
    if data.endswith("_uk_donatalerts"):
        base, dur = data.split("_")[:2]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в DonationAlerts", url=DONATION_LINK)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_uk_donatalerts")]
        ])
        await q.message.reply_text(f"DonationAlerts — Сумма: {price_display(base,dur)}\nСсылка нажмите ниже.", reply_markup=kb)
        return

    # Russia -> Donation Alerts
    if data.endswith("_ru_donatalerts"):
        base, dur = data.split("_")[:2]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в DonationAlerts", url=DONATALERTS_LINK)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_ru_donatalerts")]
        ])
        await q.message.reply_text(f"DonationAlerts — Сумма: {price_display(base,dur)}\nСсылка нажмите ниже.", reply_markup=kb)
        return

    # === FIXED: Russia -> FK Wallet handling ===
    # use endswith to be robust; show URL button + separate "Я оплатил" callback
    if data.endswith("_ru_fkwallet"):
        # data like "private_month_ru_fkwallet"
        parts = data.split("_")
        # safe parse
        if len(parts) >= 3:
            base, dur = parts[0], parts[1]
        else:
            base, dur = "private", "month"
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в FK Wallet", url=FKWALLET_LINK)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_ru_fkwallet")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ])
        instr = (
            f"💳 FK Wallet\nСумма: {price_display(base,dur)}\n\n"
            f"Инструкция:\n1) Перейдите по ссылке (кнопка выше).\n"
            "2) В кабинете выберите: Кошелёк → Рубли → Вывод.\n"
            f"3) Вставьте этот номер: {FKWALLET_NUMBER}\n"
            "4) Укажите сумму и подтвердите перевод.\n\n"
            "После оплаты нажмите '✅ Я оплатил' и пришлите скрин игры."
        )
        await q.message.reply_text(instr, reply_markup=kb)
        return

    # Kazakhstan -> Donation Alerts
    if data.endswith("_kz_donatalerts"):
        base, dur = data.split("_")[:2]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в DonationAlerts", url=DONATION_LINK)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_kz_donatalerts")]
        ])
        await q.message.reply_text(f"DonationAlerts — Сумма: {price_display(base,dur)}\nСсылка нажмите ниже.", reply_markup=kb)
        return

    # USDT -> choose network
    if data.endswith("_usdt"):
        prefix = data.replace("_usdt", "")
        await q.message.reply_text("Выберите сеть USDT:", reply_markup=usdt_network_keyboard(prefix))
        return

    if data.endswith("_usdt_trc"):
        parts = data.split("_")
        base, dur = parts[0], parts[1]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_usdt_trc")]])
        await q.message.reply_text(f"USDT TRC20 — Адрес: `{USDT_TRC20}`\nСумма: {price_display(base,dur)}\n\nПосле оплаты нажмите 'Я оплатил' и скиньте скрин игры.", parse_mode="Markdown", reply_markup=kb)
        return

    if data.endswith("_usdt_erc"):
        parts = data.split("_")
        base, dur = parts[0], parts[1]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_usdt_erc")]])
        await q.message.reply_text(f"USDT ERC20 — Адрес: `{USDT_ERC20}`\nСумма: {price_display(base,dur)}\n\nПосле оплаты нажмите 'Я оплатил' и скиньте скрин игры.", parse_mode="Markdown", reply_markup=kb)
        return

    # TON
    if data.endswith("_ton"):
        parts = data.split("_")
        base, dur = parts[0], parts[1]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_ton")]])
        await q.message.reply_text(f"TON — Адрес: `{TON_ADDRESS}`\nСумма: {price_display(base,dur)}\n\nПосле оплаты нажмите 'Я оплатил' и скиньте скрин игры.", parse_mode="Markdown", reply_markup=kb)
        return

    # CryptoBot
    if data.endswith("_cryptobot"):
        parts = data.split("_")
        base, dur = parts[0], parts[1]
        prefix = f"{base}_{dur}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в CryptoBot", url=f"https://{CRYPTOBOT_LINK}" if not CRYPTOBOT_LINK.startswith("http") else CRYPTOBOT_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_cryptobot")]])
        await q.message.reply_text(f"Оплата через CryptoBot. Сумма: {price_display(base,dur)}", reply_markup=kb)
        return

    # Stars (invoice)
    if data.endswith("_stars"):
        parts = data.split("_")
        base, dur = parts[0], parts[1]
        stars_amount = STARS_PRICES[base][dur]
        prices = [LabeledPrice("Звёзды", stars_amount)]
        payload = f"{base}_{dur}_stars"
        try:
            await q.message.reply_invoice(
                title=f"{base.title()} {dur} — Звёзды",
                description=f"Покупка {stars_amount}⭐ для {base} ({dur})",
                payload=payload,
                provider_token=STARS_PROVIDER_TOKEN,
                currency="XTR",
                prices=prices,
                start_parameter="stars")
        except Exception as e:
            logging.exception("Ошибка invoice: %s", e)
            await q.message.reply_text("Не удалось создать инвойс. Проверьте провайдера звёзд.")
        return

    # user clicked Я оплатил (any paid_... or generic "paid")
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
        await q.message.reply_text("📸 Отлично — теперь скиньте скрин оплаты/чек. Модератор проверит и выдаст ссылку в течение 2 часов.")
        # notify admin
        try:
            await context.bot.send_message(ADMIN_ID, f"Пользователь @{username} (ID: {user_id}) отметил оплату: {pack} | способ: {method}",
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Выдать ссылку", callback_data=f"give_{user_id}")]]))
        except Exception as e:
            logging.exception("Не удалось уведомить админа: %s", e)
        return

    # admin gives link button
    if data.startswith("give_"):
        if user_id != ADMIN_ID:
            await q.answer("❌ У вас нет прав администратора", show_alert=True)
            return
        try:
            target = int(data.split("_",1)[1])
        except:
            await q.answer("Неверный ID", show_alert=True)
            return
        if target in pending_users:
            pack = pending_users[target].get("pack","private_month")
            link = get_channel_link_for_pack(pack)
            try:
                await context.bot.send_message(target, f"✅ Оплата подтверждена! Ваша ссылка: {link}")
                await q.message.reply_text(f"Ссылка отправлена пользователю {target}")
                del pending_users[target]
                save_states()
            except Exception as e:
                logging.exception("Ошибка отправки ссылки: %s", e)
                await q.answer("Не удалось отправить ссылку", show_alert=True)
        else:
            await q.answer("Пользователь не в списке ожидания", show_alert=True)
        return

    # replyto_ admin state
    if data.startswith("replyto_"):
        if user_id != ADMIN_ID:
            await q.answer("Нет прав", show_alert=True)
            return
        try:
            uid = int(data.split("_",1)[1])
            admin_reply_state[user_id] = uid
            save_states()
            await q.message.reply_text(f"✍️ Отправь сообщение — оно будет переслано пользователю {uid}")
        except Exception as e:
            await q.answer("Ошибка", show_alert=True)
        return

    await q.answer()

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    if payload and payload.endswith("_stars"):
        pack = payload.replace("_stars","")
        link = get_channel_link_for_pack(pack)
        await update.message.reply_text(f"✅ Оплата успешна! Ваша ссылка: {link}")
        try:
            await context.bot.send_message(ADMIN_ID, f"Пользователь @{update.message.from_user.username or update.message.from_user.id} оплатил stars {payload}")
        except:
            pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or f"id{user_id}"
    if user_id in pending_users and pending_users[user_id].get("state") == "awaiting_screenshot":
        info = pending_users[user_id]
        pack = info.get("pack","unknown")
        method = info.get("method","unknown")
        caption = f"📸 Скрин от @{username} (ID: {user_id})\nПакет: {pack}\nМетод: {method}"
        file_id = update.message.photo[-1].file_id
        try:
            await context.bot.send_photo(ADMIN_ID, photo=file_id, caption=caption,
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Выдать ссылку", callback_data=f"give_{user_id}")]]))
            await update.message.reply_text("📨 Скрин отправлен модератору. Ожидайте проверки (до 2 часов).")
        except Exception as e:
            logging.exception("Ошибка пересылки скрина: %s", e)
            await update.message.reply_text("❌ Не удалось отправить скрин модератору. Попробуйте позже.")
        return

    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        file_id = update.message.photo[-1].file_id
        try:
            await context.bot.send_photo(ADMIN_ID, photo=file_id,
                                         caption=f"📸 Сообщение/скрин поддержки от @{username} (ID: {user_id})",
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ответить пользователю", callback_data=f"replyto_{user_id}")]]))
            await update.message.reply_text("📨 Ваше фото/сообщение отправлено в поддержку.")
        except Exception as e:
            logging.exception("Ошибка отправки поддержки: %s", e)
            await update.message.reply_text("❌ Ошибка при отправке в поддержку.")
        try:
            del pending_users[user_id]; save_states()
        except KeyError:
            pass
        return

    await update.message.reply_text("Чтобы отправить скрин игры — сначала нажмите 'Я оплатил' в меню выбранного пакета. Для поддержки нажмите '🛠 Поддержка'.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or ""

    # support flow
    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        try:
            await context.bot.send_message(ADMIN_ID, f"📨 Сообщение поддержки от @{user.username or user_id} (ID: {user_id}):\n\n{text}",
                                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ответить пользователю", callback_data=f"replyto_{user_id}")]]))
            await update.message.reply_text("✅ Ваше сообщение отправлено модератору.")
        except Exception as e:
            logging.exception("Ошибка отправки поддержки: %s", e)
            await update.message.reply_text("❌ Не удалось отправить сообщение в поддержку.")
        try:
            del pending_users[user_id]; save_states()
        except KeyError:
            pass
        return

    # admin replying state
    if user_id == ADMIN_ID and user_id in admin_reply_state:
        target = admin_reply_state[user_id]
        if not text.strip():
            await update.message.reply_text("Напишите текст для отправки пользователю.")
            return
        try:
            await context.bot.send_message(target, f"💬 Поддержка:\n\n{text}")
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {target}")
            del admin_reply_state[user_id]; save_states()
        except Exception as e:
            await update.message.reply_text(f"Ошибка отправки: {e}")
        return

    # admin replying to bot message (parse ID)
    if user_id == ADMIN_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message
        content = (orig.text or "") + "\n" + (orig.caption or "")
        m = re.search(r"ID[:\s]*([0-9]{5,})", content)
        if m:
            try:
                target = int(m.group(1))
                await context.bot.send_message(target, f"💬 Поддержка:\n\n{text}")
                await update.message.reply_text(f"✅ Ответ отправлен пользователю {target}")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {e}")
            return

    # old style /reply_
    if text.startswith("/reply_") and user_id == ADMIN_ID:
        parts = text.split(" ",1)
        cmd = parts[0]; reply_text = parts[1] if len(parts)>1 else ""
        if "_" in cmd and reply_text:
            try:
                target_id = int(cmd.replace("/reply_",""))
                await context.bot.send_message(target_id, f"💬 Поддержка:\n\n{reply_text}")
                await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {e}")
        else:
            await update.message.reply_text("Используйте: /reply_<id> текст")
        return

    # default
    await update.message.reply_text("Нажмите /start и выберите пакет. Для поддержки нажмите '🛠 Поддержка'.")

# ---------------- main ----------------
def main():
    load_states()
    keep_alive()
    if TOKEN.startswith("<") or ADMIN_ID == 0:
        print("ERROR: Вставь TOKEN и ADMIN_ID в начало файла перед запуском.")
        return

    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button))
    app_bot.add_handler(PreCheckoutQueryHandler(precheckout))
    app_bot.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен!")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

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

# --------------------- ВСТАВЬ СЮДА СВОИ ДАННЫЕ ---------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
# --------------------------------------------------------------------

STATES_FILE = "states.json"
STARS_PROVIDER_TOKEN = "STARS"

MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"  # проверь эту ссылку, может опечатка
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"
DICK_CHANNEL_LINK = "https://t.me/+--5nFyT4jjQyZDEy"

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"
DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

# In-memory structures
pending_users = {}
admin_reply_state = {}

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

# Flask для keep-alive (если используется)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    app.run(host='0.0.0.0', port=3000)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💫 Оплата звёздами (200⭐)",
                                 callback_data="pay_stars_200")
        ],
        [InlineKeyboardButton("💵 Оплата USDT 2$", callback_data="pay_usdt")],
        [InlineKeyboardButton("💎 Оплата TON 2$", callback_data="pay_ton")],
        [
            InlineKeyboardButton("🤖 Оплата через CryptoBot 2$",
                                 callback_data="pay_cryptobot")
        ],
        [
            InlineKeyboardButton(
                "🌍 Оплата для Украины, России, Казахстана и других 3$",
                callback_data="pay_donation")
        ],
        [InlineKeyboardButton("👑 VIP-приватка", callback_data="vip_menu")],
        [
            InlineKeyboardButton("🍆 Увеличение члена",
                                 callback_data="dick_menu")
        ],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])

def vip_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⭐ VIP Stars 500⭐",
                                 callback_data="vip_pay_stars_500")
        ],
        [InlineKeyboardButton("💵 USDT 5$", callback_data="vip_usdt")],
        [InlineKeyboardButton("💎 TON 5$", callback_data="vip_ton")],
        [
            InlineKeyboardButton("🤖 CryptoBot 5$",
                                 callback_data="vip_cryptobot")
        ],
        [
            InlineKeyboardButton(
                "🌍 Оплата для Украины, России, Казахстана и других 5$",
                callback_data="vip_donation")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def dick_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⭐ Увеличение Stars 250⭐",
                                 callback_data="dick_pay_stars_250")
        ],
        [InlineKeyboardButton("💵 USDT 3$", callback_data="dick_usdt")],
        [InlineKeyboardButton("💎 TON 3$", callback_data="dick_ton")],
        [
            InlineKeyboardButton("🤖 CryptoBot 3$",
                                 callback_data="dick_cryptobot")
        ],
        [
            InlineKeyboardButton(
                "🌍 Оплата для Украины, России, Казахстана и других 3$",
                callback_data="dick_donation")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def country_select_keyboard(prefix: str):
    # prefix: "donation", "vip_donation", "dick_donation"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Украина", callback_data=f"{prefix}_ukraine")],
        [InlineKeyboardButton("Россия", callback_data=f"{prefix}_russia")],
        [InlineKeyboardButton("Казахстан и другие", callback_data=f"{prefix}_kazakhstan")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def payment_options_for_ukraine(prefix: str):
    # префикс, например "donation" или "vip_donation" или "dick_donation"
    # переводим 3$ в гривны
    # курс ~ 41.38 грн за доллар (пример) :contentReference[oaicite:0]{index=0}
    uah_price = round(3 * 41.38)
    keyboard = [
        [InlineKeyboardButton(f"DonateAlerts ≈ {uah_price} грн", callback_data=f"{prefix}_ua_donatealerts")],
        [InlineKeyboardButton(f"Donatello ≈ {uah_price} грн", callback_data=f"{prefix}_ua_donatello")],
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_ua")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=prefix)]
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_options_for_russia(prefix: str):
    # рубли — примерно курс, например, 3$ ≈ 280₽ (примерно)
    rub_price = 280
    keyboard = [
        [InlineKeyboardButton(f"DonateAlerts ≈ {rub_price} ₽", callback_data=f"{prefix}_ru_donatealerts")],
        [InlineKeyboardButton(f"FK Wallet ≈ {rub_price} ₽", callback_data=f"{prefix}_ru_fkwallet")],
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_ru")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=prefix)]
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_options_for_kazakhstan(prefix: str):
    # для Казахстана просто 3$
    keyboard = [
        [InlineKeyboardButton("DonateAlerts 3$", callback_data=f"{prefix}_kz_donatealerts")],
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_kz")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=prefix)]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== ХЕЛПЕРЫ ==========

def _category_from_pack(pack: str) -> str:
    p = (pack or "").lower()
    if "vip" in p:
        return "vip"
    if "dick" in p:
        return "dick"
    return "normal"

# ========== ХЭНДЛЕРЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"),
        reply_markup=main_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    data = query.data

    # кнопка Назад
    if data == "back":
        await query.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"),
            reply_markup=main_keyboard()
        )
        return

    # поддержка
    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        await query.message.reply_text("🛠 Напишите своё сообщение поддержки. Мы перешлём его модератору.")
        return

    # reply админ → пользователь
    if data.startswith("replyto_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        target = int(data.split("_", 1)[1])
        admin_reply_state[user_id] = target
        save_states()
        await query.message.reply_text(f"✍️ Отправь сообщение — оно будет переслано пользователю {target}.")
        return

    # Оплата звёздами
    if data == "pay_stars_200":
        prices = [LabeledPrice("Доступ в приват", 200)]
        await query.message.reply_invoice(
            title="Вход в приват",
            description="Оплата за доступ к приватному каналу",
            payload="privat-200stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="stars"
        )
        return

    if data == "vip_pay_stars_500":
        prices = [LabeledPrice("VIP-приват", 500)]
        await query.message.reply_invoice(
            title="VIP-приватка",
            description="Оплата за VIP-приватку",
            payload="vip-500stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="vipstars"
        )
        return

    if data == "dick_pay_stars_250":
        prices = [LabeledPrice("Увеличение члена", 250)]
        await query.message.reply_invoice(
            title="🍆 Увеличение члена",
            description="Оплата услуги увеличения члена",
            payload="dick-250stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="dickstars"
        )
        return

    # USDT обычная
    if data == "pay_usdt":
        keyboard = [[InlineKeyboardButton("USDT TRC20", callback_data="pay_usdt_trc")],
                    [InlineKeyboardButton("USDT ERC20", callback_data="pay_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text("💵 Выберите сеть для оплаты USDT (2$):",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_usdt_trc":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_usdt_trc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT TRC20\nСумма: 2$\nАдрес: `{USDT_TRC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "pay_usdt_erc":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT ERC20\nСумма: 2$\nАдрес: `{USDT_ERC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # VIP USDT
    if data == "vip_usdt":
        keyboard = [[InlineKeyboardButton("USDT TRC20", callback_data="vip_usdt_trc")],
                    [InlineKeyboardButton("USDT ERC20", callback_data="vip_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text("💵 Выберите сеть для VIP USDT (5$):",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "vip_usdt_trc":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_usdt_trc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 VIP Оплата USDT TRC20\nСумма: 5$\nАдрес: `{USDT_TRC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "vip_usdt_erc":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 VIP Оплата USDT ERC20\nСумма: 5$\nАдрес: `{USDT_ERC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # TON обычная
    if data == "pay_ton":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_ton")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 2$\nАдрес: `{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # CryptoBot обычная
    if data == "pay_cryptobot":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_cryptobot")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 2$",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # VIP TON
    if data == "vip_ton":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_ton")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 5$\nАдрес: `{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # VIP CryptoBot
    if data == "vip_cryptobot":
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_cryptobot")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 5$",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # VIP / обычная / dick — кнопки выбора стран для оплаты
    if data == "pay_donation":
        await query.message.reply_text(
            "Выберите страну для оплаты:",
            reply_markup=country_select_keyboard("donation")
        )
        return

    if data == "vip_donation":
        await query.message.reply_text(
            "Выберите страну для оплаты:",
            reply_markup=country_select_keyboard("vip_donation")
        )
        return

    if data == "dick_donation":
        await query.message.reply_text(
            "Выберите страну для оплаты:",
            reply_markup=country_select_keyboard("dick_donation")
        )
        return

    # после выбора страны — показываем варианты оплаты
    if data.endswith("_ukraine") and ("donation" in data or "vip_donation" in data or "dick_donation" in data):
        prefix = data.rsplit("_", 1)[0]
        await query.message.reply_text(
            "Выберите способ оплаты (Украина):",
            reply_markup=payment_options_for_ukraine(prefix)
        )
        return

    if data.endswith("_russia") and ("donation" in data or "vip_donation" in data or "dick_donation" in data):
        prefix = data.rsplit("_", 1)[0]
        await query.message.reply_text(
            "Выберите способ оплаты (Россия):",
            reply_markup=payment_options_for_russia(prefix)
        )
        return

    if data.endswith("_kazakhstan") and ("donation" in data or "vip_donation" in data or "dick_donation" in data):
        prefix = data.rsplit("_", 1)[0]
        await query.message.reply_text(
            "Выберите способ оплаты (Казахстан и другие):",
            reply_markup=payment_options_for_kazakhstan(prefix)
        )
        return

    # Универсальный “Я оплатил” для стран
    if data.startswith("paid_"):
        pack = data.replace("paid_", "")
        category = _category_from_pack(pack)
        pending_users[user_id] = {"state": "awaiting_screenshot", "pack": pack, "category": category}
        save_states()
        await query.message.reply_text(
            "✅ Нажато: 'Я оплатил'. Пожалуйста, отправьте скрин оплаты — модератор проверит и выдаст ссылку."
        )
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"Пользователь @{user.username or user_id} (ID: {user_id}) отметил оплату: {pack}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Выдать ссылку @{user.username or user_id}", callback_data=f"give_{user_id}")]])
            )
        except Exception as e:
            logging.exception("Не удалось уведомить админа о пометке оплаты: %s", e)
        return

    # Админ выдает ссылку
    if data.startswith("give_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        target_id = int(data.split("_", 1)[1])
        if target_id in pending_users:
            info = pending_users[target_id]
            category = info.get("category", "normal")
            if category == "vip":
                link = VIP_CHANNEL_LINK
            elif category == "dick":
                link = DICK_CHANNEL_LINK
            else:
                link = CHANNEL_LINK
            try:
                await context.bot.send_message(
                    target_id,
                    f"✅ Оплата подтверждена! Вот ссылка на канал:\n{link}"
                )
                await query.answer(f"Ссылка отправлена пользователю {target_id}")
                del pending_users[target_id]
                save_states()
            except Exception as e:
                logging.exception("Не удалось отправить ссылку пользователю: %s", e)
                await query.answer("❌ Не удалось отправить ссылку пользователю.", show_alert=True)
        else:
            await query.answer("Пользователь не найден в списке ожидающих оплат.", show_alert=True)
        return

    # PreCheckout для звезд (Stars)
    if data.startswith("privat") or data.startswith("vip") or data.startswith("dick"):
        # ничего не делаем здесь, это handled выше
        pass

    # Неизвестная кнопка fallback
    await query.answer()

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    payload = payment.invoice_payload
    if payload in ["privat-200stars", "vip-500stars", "dick-250stars"]:
        if "vip" in payload:
            link = VIP_CHANNEL_LINK
        elif "dick" in payload:
            link = DICK_CHANNEL_LINK
        else:
            link = CHANNEL_LINK
        await update.message.reply_text(f"✅ Оплата успешна!\nВот ссылка на канал:\n{link}")
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"Пользователь @{update.message.from_user.username or user_id} (ID: {user_id}) оплатил {payload}"
            )
        except Exception:
            pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or "без_username"

    if user_id in pending_users:
        state = pending_users[user_id].get("state")
        if state == "awaiting_screenshot":
            info = pending_users[user_id]
            pack = info.get("pack", "unknown")
            category = info.get("category", "normal")
            if category == "vip":
                caption_type = "👑 VIP приватка"
            elif category == "dick":
                caption_type = "🍆 Dick приватка"
            else:
                caption_type = "💫 Обычный доступ"

            keyboard = [[
                InlineKeyboardButton(f"Выдать ссылку @{username}", callback_data=f"give_{user_id}")
            ]]
            try:
                await context.bot.send_photo(
                    ADMIN_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=f"📸 Скрин оплаты от @{username} (ID: {user_id})\nПакет: {pack} | {caption_type}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
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

    await update.message.reply_text(
        "❗ Чтобы отправить скрин оплаты, сначала нажмите кнопку '✅ Я оплатил' в меню нужного пакета.\n"
        "Для поддержки нажмите кнопку '🛠 Поддержка'."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or ""
    username = user.username or "без_username"

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

    if user_id == ADMIN_ID and user_id in admin_reply_state:
        target_id = admin_reply_state[user_id]
        if not text.strip():
            await update.message.reply_text("❗ Напишите текст, чтобы отправить ответ пользователю.")
            return
        try:
            await context.bot.send_message(target_id, f"💬 Поддержка: {text}")
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
        try:
            del admin_reply_state[user_id]
            save_states()
        except KeyError:
            pass
        return

    if user_id == ADMIN_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message
        content = (orig.text or "") + "\n" + (orig.caption or "")
        m = re.search(r"ID[:\s]*([0-9]{5,})", content)
        if m:
            target = int(m.group(1))
            if not text.strip():
                await update.message.reply_text("❗ Напишите текст, чтобы отправить ответ пользователю.")
                return
            await context.bot.send_message(target, f"💬 Поддержка: {text}")
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {target}")
            return

    if text.startswith("/reply_") and user_id == ADMIN_ID:
        parts = text.split(" ", 1)
        cmd = parts[0]
        reply_text = parts[1] if len(parts) > 1 else ""
        if "_" in cmd and reply_text:
            try:
                target_id = int(cmd.replace("/reply_", ""))
                try:
                    await context.bot.send_message(target_id, f"💬 Поддержка: {reply_text}")
                    await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
                except Exception as e:
                    await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID. Используйте /reply_<id> текст")
        else:
            await update.message.reply_text("❌ Используйте формат: /reply_<id> текст")
        return

    await update.message.reply_text(
        "Если вы хотите оплатить — нажмите /start и выберите пакет. Для поддержки нажмите кнопку '🛠 Поддержка'."
    )

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


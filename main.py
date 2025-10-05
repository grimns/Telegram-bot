from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ContextTypes, MessageHandler, filters,
                          PreCheckoutQueryHandler)
from flask import Flask
from threading import Thread
import logging
import re

logging.basicConfig(level=logging.INFO)

# ================== НАСТРОЙКИ ==================
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923

STARS_PROVIDER_TOKEN = "STARS"

MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"
DICK_CHANNEL_LINK = "https://t.me/+--5nFyT4jjQyZDEy"  # <-- поменяй на свой, если нужно

USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"
DONATION_LINK = "https://www.donationalerts.com/r/gromn"

IMAGE_URL = "https://ibb.co/hxbvxM4L"

pending_users = {}  # {user_id: pack_type}
admin_reply_state = {}  # {admin_id: user_id_to_reply}

# ================== FLASK keep-alive ==================
app = Flask('')


@app.route('/')
def home():
    return "Bot is running"


def run():
    app.run(host='0.0.0.0', port=3000)


def keep_alive():
    t = Thread(target=run)
    t.start()


# ================== КЛАВИАТУРЫ ==================
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💫 Оплата звёздами (200⭐)",
                                 callback_data="pay_stars_200")
        ],
        [InlineKeyboardButton("💵 Оплата USDT 3$", callback_data="pay_usdt")],
        [InlineKeyboardButton("💎 Оплата TON 3$", callback_data="pay_ton")],
        [
            InlineKeyboardButton("🤖 Оплата через CryptoBot 3$",
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
        [InlineKeyboardButton("💵 USDT 10$", callback_data="vip_usdt")],
        [InlineKeyboardButton("💎 TON 10$", callback_data="vip_ton")],
        [
            InlineKeyboardButton("🤖 CryptoBot 10$",
                                 callback_data="vip_cryptobot")
        ],
        [
            InlineKeyboardButton(
                "🌍 Оплата для Украины, России, Казахстана и других 10$",
                callback_data="vip_donation")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def dick_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⭐ Увеличение Stars 350⭐",
                                 callback_data="dick_pay_stars_350")
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


# ================== СТАРТ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=(
            f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"
        ),
        reply_markup=main_keyboard())


# ================== ОБРАБОТКА КНОПОК ==================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    data = query.data

    # Кнопка Назад
    if data == "back":
        await query.message.reply_photo(
            photo=IMAGE_URL,
            caption=
            (f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"
             ),
            reply_markup=main_keyboard())
        return

    # ===== Поддержка (пометка) =====
    if data == "support":
        pending_users[user_id] = "support"
        await query.message.reply_text(
            "🛠 Напишите своё сообщение поддержки. Мы перешлём его модератору.")
        return

    # ===== Админ отвечает через кнопку "Ответить пользователю" (устанавливаем state) =====
    if data.startswith("replyto_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.",
                               show_alert=True)
            return
        try:
            target = int(data.split("_", 1)[1])
        except Exception:
            await query.answer("❌ Неверный идентификатор.", show_alert=True)
            return
        admin_reply_state[user_id] = target
        await query.message.reply_text(
            f"✍️ Отправь сообщение — оно будет переслано пользователю {target}."
        )
        return

    # ===== Оплата звёздами (обычная) =====
    if data == "pay_stars_200":
        prices = [LabeledPrice("Доступ в приват", 200)]
        await query.message.reply_invoice(
            title="Вход в приват",
            description="Оплата за доступ к приватному каналу",
            payload="privat-200stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="stars")
        return

    # ===== VIP stars =====
    if data == "vip_pay_stars_500":
        prices = [LabeledPrice("VIP-приват", 500)]
        await query.message.reply_invoice(title="VIP-приватка",
                                          description="Оплата за VIP-приватку",
                                          payload="vip-500stars",
                                          provider_token=STARS_PROVIDER_TOKEN,
                                          currency="XTR",
                                          prices=prices,
                                          start_parameter="vipstars")
        return

    # ===== Обычная USDT (выбор сети) =====
    if data == "pay_usdt":
        keyboard = [[
            InlineKeyboardButton("USDT TRC20", callback_data="pay_usdt_trc")
        ], [InlineKeyboardButton("USDT ERC20", callback_data="pay_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            "💵 Выберите сеть для оплаты USDT (3$):",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_usdt_trc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_pay_usdt_trc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT TRC20\nСумма: 3$\nАдрес: `{USDT_TRC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_usdt_erc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_pay_usdt_erc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT ERC20\nСумма: 3$\nАдрес: `{USDT_ERC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== VIP USDT (выбор сети) =====
    if data == "vip_usdt":
        keyboard = [[
            InlineKeyboardButton("USDT TRC20", callback_data="vip_usdt_trc")
        ], [InlineKeyboardButton("USDT ERC20", callback_data="vip_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            "💵 Выберите сеть для VIP USDT (10$):",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "vip_usdt_trc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_vip_usdt_trc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 VIP Оплата USDT TRC20\nСумма: 10$\nАдрес: `{USDT_TRC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "vip_usdt_erc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_vip_usdt_erc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 VIP Оплата USDT ERC20\nСумма: 10$\nАдрес: `{USDT_ERC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== Остальные оплаты (общие) =====
    if data == "pay_ton":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_pay_ton")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 3$\nАдрес: `{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_cryptobot":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_pay_cryptobot")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 3$",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_donation":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_pay_donation")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🌍 Оплата для Украины, России, Казахстана и других\nСумма: 3$\nСсылка: {DONATION_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== VIP меню =====
    if data == "vip_menu":
        await query.message.reply_text(
            "👑 VIP-приватка. Выберите способ оплаты:",
            reply_markup=vip_keyboard())
        return

    if data == "vip_ton":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_vip_ton")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 10$\nАдрес: `{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "vip_cryptobot":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_vip_cryptobot")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 10$",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "vip_donation":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_vip_donation")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🌍 Оплата для Украины, России, Казахстана и других\nСумма: 10$\nСсылка: {DONATION_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== УВЕЛИЧЕНИЕ ЧЛЕНА (замена Игры) =====
    if data == "dick_menu":
        await query.message.reply_text(
            "🍆 Увеличение члена. Цена: 250₽ / 3 USDT / 350⭐\nВыберите способ оплаты:",
            reply_markup=dick_keyboard())
        return

    if data == "dick_pay_stars_350":
        prices = [LabeledPrice("Увеличение члена", 350)]
        await query.message.reply_invoice(
            title="🍆 Увеличение члена",
            description="Оплата услуги увеличения члена",
            payload="dick-350stars",
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="dickstars")
        return

    if data == "dick_usdt":
        keyboard = [[
            InlineKeyboardButton("USDT TRC20", callback_data="dick_usdt_trc")
        ], [InlineKeyboardButton("USDT ERC20", callback_data="dick_usdt_erc")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            "💵 Выберите сеть для оплаты USDT (3$):",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "dick_usdt_trc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_dick_usdt_trc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT TRC20\nСумма: 3$\nАдрес: `{USDT_TRC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "dick_usdt_erc":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data="paid_dick_usdt_erc")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT ERC20\nСумма: 3$\nАдрес: `{USDT_ERC20}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "dick_ton":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_dick_ton")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 3$\nАдрес: `{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "dick_cryptobot":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_dick_cryptobot")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 3$",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "dick_donation":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил",
                                 callback_data=f"paid_dick_donation")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🌍 Оплата для Украины, России, Казахстана и других\nСумма: 3$\nСсылка: {DONATION_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ===== Универсальная логика: пользователь нажал "✅ Я оплатил" =====
    # ЭТА ЧАСТЬ ХРАНИТ pack (например: "dick_usdt_trc", "pay_usdt_trc", "vip_usdt_trc", "pay_dick_usdt_trc", "vip", "dick" и т.д.)
    if data.startswith("paid_"):
        pack = data.replace("paid_", "")
        pending_users[user_id] = pack
        # Сообщаем пользователю
        await query.message.reply_text(
            "✅ Скиньте скрин оплаты, модератор проверит и скинет вам ссылку.")
        # Сообщаем админу, что пользователь отметил оплату (и даём кнопку выдать ссылку сразу)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"Пользователь @{user.username or user_id} (ID: {user_id}) отметил оплату: {pack}.\n"
                "Отправьте скрин сюда или нажмите кнопку, чтобы выдать ссылку:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        f"Выдать ссылку {user.username or user_id}",
                        callback_data=f"give_{user_id}")
                ]]))
        except Exception as e:
            logging.exception(
                "Не удалось уведомить админа о пометке оплаты: %s", e)
        return

    # ===== Админ выдал ссылку кнопкой =====
    if data.startswith("give_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.",
                               show_alert=True)
            return
        try:
            target_id = int(data.split("_", 1)[1])
        except Exception:
            await query.answer("❌ Неверный идентификатор.", show_alert=True)
            return
        if target_id in pending_users:
            method = pending_users[target_id]
            # определяем куда слать ссылку
            if "vip" in method:
                link = VIP_CHANNEL_LINK
            elif "dick" in method:
                link = DICK_CHANNEL_LINK
            else:
                link = CHANNEL_LINK
            await context.bot.send_message(
                target_id,
                f"✅ Оплата подтверждена! Вот ссылка на канал:\n{link}")
            await query.answer(f"Ссылка отправлена пользователю {target_id}")
            del pending_users[target_id]
        else:
            await query.answer(
                "Пользователь не найден в списке ожидающих оплат.",
                show_alert=True)
        return

    # Если попали сюда — неизвестная кнопка (на всякий случай)
    await query.answer()


# ================== PreCheckout (Stars) ==================
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


# ================== Успешная оплата Stars ==================
async def successful_payment(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    payload = payment.invoice_payload

    # payload'ы соответствуют инвойсам выше
    if payload in ["privat-200stars", "vip-500stars", "dick-350stars"]:
        if "vip" in payload:
            link = VIP_CHANNEL_LINK
        elif "dick" in payload:
            link = DICK_CHANNEL_LINK
        else:
            link = CHANNEL_LINK
        # автоматически выдаём ссылку пользователю
        await update.message.reply_text(
            f"✅ Оплата успешна!\nВот ссылка на канал:\n{link}")
        await context.bot.send_message(
            ADMIN_ID,
            f"Пользователь @{update.message.from_user.username or user_id} (ID: {user_id}) оплатил {payload}"
        )


# ================== Обработка фото (скриншоты) ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or "без_username"

    # если пользователь нажал "Я оплатил" ранее — ожидаем скрин
    if user_id in pending_users and pending_users[user_id] != "support":
        pack = pending_users[user_id]
        # Пересылаем админу фото + кнопка для выдачи ссылки
        keyboard = [[
            InlineKeyboardButton(f"Выдать ссылку @{user.username or user_id}",
                                 callback_data=f"give_{user_id}")
        ]]
        await context.bot.send_photo(
            ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=
            f"📸 Скрин оплаты от @{username} (ID: {user_id})\nПакет: {pack}",
            reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text(
            "📨 Скрин отправлен модератору, ожидайте проверки.")
    elif user_id in pending_users and pending_users[user_id] == "support":
        # пользователь писал в поддержку фото — пересылаем админу, добавляем кнопку "Ответить"
        await context.bot.send_photo(
            ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=
            f"📸 Сообщение/скрин поддержки от @{username} (ID: {user_id})",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 Ответить пользователю",
                                     callback_data=f"replyto_{user_id}")
            ]]))
        await update.message.reply_text(
            "📨 Ваше фото/сообщение отправлено в поддержку.")
        del pending_users[user_id]
    else:
        # пользователь прислал фото без пометки оплаты
        await update.message.reply_text(
            "❗ Чтобы отправить скрин оплаты, сначала нажмите кнопку '✅ Я оплатил' в меню нужного пакета."
        )


# ================== Обработка текста (поддержка и reply команда) ==================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or ""
    username = user.username or "без_username"

    # ---------------- user -> support: пересылаем админу с кнопкой ----------------
    if user_id in pending_users and pending_users[user_id] == "support":
        # отправляем админу сообщение + кнопка ответить
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📨 Сообщение поддержки от @{username} (ID: {user_id}):\n\n{text}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Ответить пользователю",
                                         callback_data=f"replyto_{user_id}")
                ]]))
            await update.message.reply_text(
                "✅ Ваше сообщение отправлено. Ожидайте ответ.")
        except Exception as e:
            logging.exception("Ошибка при отправке поддержки админу: %s", e)
            await update.message.reply_text(
                "❌ Не удалось отправить сообщение в поддержку. Попробуйте позже."
            )
        # удаляем пометку поддержки
        del pending_users[user_id]
        return

    # ---------------- admin: отвечает после нажатия кнопки (stateful) ----------------
    if user_id == ADMIN_ID and user_id in admin_reply_state:
        target_id = admin_reply_state[user_id]
        if not text.strip():
            await update.message.reply_text(
                "❗ Напишите текст, чтобы отправить ответ пользователю.")
            return
        try:
            await context.bot.send_message(target_id, f"💬 Поддержка: {text}")
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю {target_id}")
        except Exception as e:
            await update.message.reply_text(
                f"❌ Не удалось отправить сообщение пользователю: {e}")
        # очищаем состояние
        del admin_reply_state[user_id]
        return

    # ---------------- admin: ответ через reply (ответ на сообщении бота в чате админа) ----------------
    # если админ ответил прямо на сообщении бота, пытаемся вытащить ID пользователя из текста/подписи
    if user_id == ADMIN_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message
        content = (orig.text or "") + "\n" + (orig.caption or "")
        m = re.search(r"ID[:\s]*([0-9]{5,})", content)
        if m:
            try:
                target = int(m.group(1))
                if not text.strip():
                    await update.message.reply_text(
                        "❗ Напишите текст, чтобы отправить ответ пользователю."
                    )
                    return
                await context.bot.send_message(target, f"💬 Поддержка: {text}")
                await update.message.reply_text(
                    f"✅ Ответ отправлен пользователю {target}")
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Не удалось отправить сообщение пользователю: {e}")
            return

    # ---------------- admin: старый вариант /reply_<id> ----------------
    if text.startswith("/reply_") and user_id == ADMIN_ID:
        parts = text.split(" ", 1)
        cmd = parts[0]
        reply_text = parts[1] if len(parts) > 1 else ""
        if "_" in cmd and reply_text:
            try:
                target_id = int(cmd.replace("/reply_", ""))
                try:
                    await context.bot.send_message(
                        target_id, f"💬 Поддержка: {reply_text}")
                    await update.message.reply_text(
                        f"✅ Ответ отправлен пользователю {target_id}")
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ Не удалось отправить сообщение пользователю: {e}")
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат ID. Используйте /reply_<id> текст")
        else:
            await update.message.reply_text(
                "❌ Используйте формат: /reply_<id> текст")
        return

    # если обычный текст и не поддержка — подсказка
    await update.message.reply_text(
        "Если вы хотите оплатить — нажмите /start и выберите пакет. Для поддержки нажмите кнопку '🛠 Поддержка'."
    )


# ================== ЗАПУСК ==================
def main():
    keep_alive()
    app_bot = Application.builder().token(TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button))
    app_bot.add_handler(PreCheckoutQueryHandler(precheckout))
    app_bot.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # reply команда также обрабатывается в handle_text (как в оригинале)

    print("Бот запущен!")
    app_bot.run_polling()


if __name__ == "__main__":
    main()

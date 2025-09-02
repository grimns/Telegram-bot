from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread

# === Настройки ===
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"
MAIN_CHANNEL = "https://t.me/osnvkanal"
DONATION_LINK = "https://www.donationalerts.com/r/gromn"
IMAGE_URL = "https://ibb.co/hxbvxM4L"
ADMIN_ID = 1758979923  # твой Telegram ID

pending_users = {}

# === Flask для keep_alive ===
app = Flask('')


@app.route('/')
def home():
    return "Bot is running"


def run():
    app.run(host='0.0.0.0', port=3000)


def keep_alive():
    t = Thread(target=run)
    t.start()


# === Клавиатуры ===
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💵 Оплата USDT", callback_data="pay_usdt")],
        [InlineKeyboardButton("💎 Оплата TON", callback_data="pay_ton")],
        [
            InlineKeyboardButton("🤖 Оплата через CryptoBot",
                                 callback_data="pay_cryptobot")
        ],
        [InlineKeyboardButton("💫 Оплата звёздами", callback_data="pay_stars")],
        [
            InlineKeyboardButton(
                "🌍 Оплата для Украины, России, Казахстана и других",
                callback_data="pay_donation")
        ], [InlineKeyboardButton("🛠 Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])


# === Старт бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=(
            f"📢 Наш основной канал: {MAIN_CHANNEL}\n\n"
            "Вы хотите купить доступ? Стоимость: 3$\nВыберите способ оплаты:"),
        reply_markup=main_keyboard())


# === Обработка кнопок ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id

    if query.data == "back":
        await query.message.reply_photo(
            photo=IMAGE_URL,
            caption=
            (f"📢 Наш основной канал: {MAIN_CHANNEL}\n\n"
             "Вы хотите купить доступ? Стоимость: 3$\nВыберите способ оплаты:"
             ),
            reply_markup=main_keyboard())

    elif query.data == "pay_stars":
        await query.message.reply_text(
            "💫 Оплата звёздами временно недоступна.",
            reply_markup=back_keyboard())

    elif query.data == "pay_usdt":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data="paid_usdt")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💵 Оплата USDT\nСумма: 3$\nПереведите на адрес:\n`{USDT_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "pay_ton":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data="paid_ton")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"💎 Оплата TON\nСумма: 3$\nПереведите на адрес:\n`{TON_ADDRESS}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "pay_cryptobot":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data="paid_cryptobot")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 3$",
            reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "pay_donation":
        keyboard = [[
            InlineKeyboardButton("✅ Я оплатил", callback_data="paid_donation")
        ], [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            f"🌍 Оплата для Украины, России, Казахстана и других\nСумма: 3$\nПерейдите по ссылке:\n{DONATION_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "support":
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            "🛠 Напишите ваше сообщение поддержки ниже, и оно придет модератору. "
            "Ответ придет обратно через этого бота анонимно.",
            reply_markup=InlineKeyboardMarkup(keyboard))
        pending_users[user_id] = "SUPPORT"

    elif query.data.startswith("paid_"):
        pay_type = query.data.replace("paid_", "").upper()
        pending_users[user_id] = pay_type
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        await query.message.reply_text(
            "✅ Спасибо! Скиньте скрин оплаты в течение 5 часов, модератор проверит и скинет вам ссылку.",
            reply_markup=InlineKeyboardMarkup(keyboard))
        await context.bot.send_message(
            ADMIN_ID,
            f"Пользователь @{user.username} (ID: {user.id}) оплатил через {pay_type}.\n"
            "Отправьте скрин сюда или нажмите кнопку ниже, чтобы выдать ссылку.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"Выдать ссылку {user.username}",
                                     callback_data=f"give_{user_id}")
            ]]))

    elif query.data.startswith("give_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.",
                               show_alert=True)
            return
        target_id = int(query.data.split("_")[1])
        if target_id in pending_users:
            await context.bot.send_message(
                target_id,
                f"✅ Оплата подтверждена! Вот ссылка на канал:\n{CHANNEL_LINK}")
            await query.answer(f"Ссылка отправлена пользователю {target_id}")
            del pending_users[target_id]
        else:
            await query.answer(
                "Пользователь не найден в списке ожидающих оплат.",
                show_alert=True)


# === Обработка скриншотов ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        return
    await context.bot.send_photo(
        ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"Скрин оплаты от @{user.username} (ID: {user.id})")
    await update.message.reply_text(
        "📨 Скрин отправлен модератору, ожидайте проверки и ссылку.")


# === Обработка сообщений поддержки ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text

    if user_id in pending_users and pending_users[user_id] == "SUPPORT":
        await context.bot.send_message(
            ADMIN_ID,
            f"📨 Сообщение поддержки от @{user.username} (ID: {user.id}):\n{text}\n\n"
            f"Чтобы ответить, отправьте сообщение в формате:\n"
            f"/reply_{user_id} ТЕКСТ_ОТВЕТА")
        await update.message.reply_text(
            "✅ Ваше сообщение отправлено. Ожидайте ответ.")
        del pending_users[user_id]


# === Команда ответа админа ===
async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    msg = update.message.text
    parts = msg.split(" ", 1)
    cmd = parts[0]
    reply_text = parts[1] if len(parts) > 1 else ""

    if "_" in cmd and reply_text:
        target_id = int(cmd.split("_")[1])
        await context.bot.send_message(target_id, f"💬 Поддержка: {reply_text}")
        await update.message.reply_text(
            f"✅ Ответ отправлен пользователю {target_id}")


# === Запуск бота ===
def main():
    keep_alive()
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_bot.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^/reply_\d+"),
                       reply_command))
    print("Бот запущен!")
    app_bot.run_polling()


if __name__ == "__main__":
    main()


import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# --------------------- ТВОИ ДАННЫЕ ---------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
STATES_FILE = "states.json"

# ссылки на каналы/пакеты
MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"     # обычный приват
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"  # VIP
DICK_CHANNEL_LINK = "https://t.me/+--5nFyT4jjQyZDEy" # Dick (увеличение)

# Кошельки/ссылки
USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATION_LINK = "https://www.donationalerts.com/r/gromn"
DONATELLO_LINK = "https://donatello.to/Gromn"
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"

# --------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---------------------
def save_state(state):
    with open(STATES_FILE, "w") as f:
        json.dump(state, f)

def load_state():
    try:
        with open(STATES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# --------------------- START ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Обычный приват", callback_data="private")],
        [InlineKeyboardButton("VIP-приват", callback_data="vip")],
        [InlineKeyboardButton("Увеличение члена", callback_data="dick")]
    ])
    await update.message.reply_text("Привет! Выберите категорию:", reply_markup=kb)

# --------------------- CALLBACK QUERY ---------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "private":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплата Украина", callback_data="pay_ua")],
            [InlineKeyboardButton("Оплата Россия", callback_data="pay_ru")],
            [InlineKeyboardButton("Оплата Казахстан", callback_data="pay_kz")],
            [InlineKeyboardButton("Другие страны", callback_data="pay_other")],
            [InlineKeyboardButton("Ссылки на канал", url=CHANNEL_LINK)]
        ])
        await query.message.reply_text("Выберите страну для оплаты:", reply_markup=kb)

    elif query.data in ["vip", "dick"]:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплата USDT (TRC20)", callback_data="usdt_trc")],
            [InlineKeyboardButton("Оплата USDT (ERC20)", callback_data="usdt_erc")],
            [InlineKeyboardButton("Оплата TON", callback_data="ton")],
            [InlineKeyboardButton("Ссылки на канал", url=VIP_CHANNEL_LINK if query.data=="vip" else DICK_CHANNEL_LINK)]
        ])
        await query.message.reply_text("Выберите способ оплаты:", reply_markup=kb)

    elif query.data.startswith("pay_"):
        country = query.data.split("_")[1]
        if country in ["ua", "ru", "kz"]:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Donat Alerts", url=DONATION_LINK)],
                [InlineKeyboardButton("Donatello", url=DONATELLO_LINK)],
                [InlineKeyboardButton("FKWallet", url=FKWALLET_LINK)],
                [InlineKeyboardButton("Я оплатил", callback_data=f"paid_{country}")]
            ])
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Donat Alerts", url=DONATION_LINK)],
                [InlineKeyboardButton("Я оплатил", callback_data=f"paid_other")]
            ])
        await query.message.reply_text("Выберите способ оплаты:", reply_markup=kb)

    elif query.data.startswith("usdt_") or query.data == "ton":
        text = "Для оплаты используйте следующий адрес:\n"
        if query.data == "usdt_trc":
            text += f"USDT TRC20: {USDT_TRC20}"
        elif query.data == "usdt_erc":
            text += f"USDT ERC20: {USDT_ERC20}"
        elif query.data == "ton":
            text += f"TON: {TON_ADDRESS}"
        await query.message.reply_text(text + f"\n\nПосле оплаты нажмите 'Я оплатил'.")
    
    elif query.data.startswith("paid_"):
        state = load_state()
        user_id = str(query.from_user.id)
        state[user_id] = {"awaiting_screenshot": True}
        save_state(state)
        await query.message.reply_text("Отправьте скрин оплаты или чек.")

    elif query.data.startswith("give_link_"):
        user_id = query.data.split("_")[2]
        # отправка ссылки пользователю
        await context.bot.send_message(chat_id=int(user_id), text="Вот ваша ссылка: "+MAIN_CHANNEL)
        await query.message.delete()

# --------------------- HANDLER ФОТО И СКРИН ---------------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    user_id = str(update.message.from_user.id)
    if state.get(user_id, {}).get("awaiting_screenshot"):
        # пересылаем админу
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f"Скрин от {update.message.from_user.id}")
        # добавляем кнопку "Выдать ссылку"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Выдать ссылку", callback_data=f"give_link_{user_id}")]])
        await context.bot.send_message(chat_id=ADMIN_ID, text="Выдать ссылку:", reply_markup=kb)
        state[user_id]["awaiting_screenshot"] = False
        save_state(state)
        await update.message.reply_text("Скрин получен, ждите выдачи ссылки.")

# --------------------- MAIN ---------------------
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    app.run_polling()

if __name__ == "__main__":
    main()

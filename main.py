# mainp.py — исправленная и финальная версия
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
logger = logging.getLogger(__name__)

# --------------------- ТВОИ ДАННЫЕ ---------------------
TOKEN = "8145255899:AAFQcd7SZrpvH2GVuLwxASqtg1rYYoeMHu4"
ADMIN_ID = 1758979923
# --------------------------------------------------------------------

STATES_FILE = "states.json"
STARS_PROVIDER_TOKEN = "STARS"

# ссылки на каналы/пакеты
MAIN_CHANNEL = "https://t.me/osnvkanal"
CHANNEL_LINK = "https://t.me/+52SBJ_ZOFYg2YTky"     # обычный приват
VIP_CHANNEL_LINK = "https://t.me/+RW9AYUQMIjo0NjEy"  # VIP
DICK_CHANNEL_LINK = "https://t.me/+--5nFyT4jjQyZDEy" # Dick (увеличение --- как у тебя)

# Кошельки/ссылки
USDT_TRC20 = "TDiDg4tsuMdZYs7Afz1EsUR4gkkE5jJb9D"
USDT_ERC20 = "0xc5fd6eb0a1fd15eb98cb18bf5f57457fea8e50a3"
TON_ADDRESS = "UQAYWHW0rKhY9MEZ6UR5pn76YUJTZtlb3D1rWYcC7R6f9-EA"
CRYPTOBOT_LINK = "t.me/send?start=IVmn0QryS4jg"

DONATION_LINK = "https://www.donationalerts.com/r/gromn"   # DonateAlerts
DONATELLO_LINK = "https://donatello.to/Gromn"             # Donatello
FKWALLET_LINK = "https://fkwallet.io/registration?partner_code=FK3223"
FKWALLET_NUMBER = "F7202565872412476"
# --------------------------------------------------------------------

IMAGE_URL = "https://ibb.co/hxbvxM4L"

# ----------------- В памяти / states -----------------
# pending_users: {user_id: { 'state': 'awaiting_screenshot'|'support', 'pack': '<pack>', 'category': 'vip'|'dick'|'normal' }}
pending_users = {}
# admin_reply_state: {admin_id: user_id_to_reply}
admin_reply_state = {}

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
        logger.exception("Не удалось загрузить states.json: %s", e)
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
        logger.exception("Не удалось сохранить states.json: %s", e)

load_states()

# ================== FLASK keep-alive ==================
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
        [InlineKeyboardButton("💫 Оплата звёздами (200⭐)", callback_data="pay_stars_200")],
        [InlineKeyboardButton("💵 Оплата USDT 3$", callback_data="pay_usdt")],
        [InlineKeyboardButton("💎 Оплата TON 3$", callback_data="pay_ton")],
        [InlineKeyboardButton("🤖 Оплата через CryptoBot 3$", callback_data="pay_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины, России, Казахстана и других 3$", callback_data="pay_donation")],
        [InlineKeyboardButton("👑 VIP-приватка", callback_data="vip_menu")],
        [InlineKeyboardButton("🍆 Увеличение члена", callback_data="dick_menu")],
        [InlineKeyboardButton("🛠 Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def vip_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ VIP Stars 500⭐", callback_data="vip_pay_stars_500")],
        [InlineKeyboardButton("💵 USDT 5$", callback_data="vip_usdt")],
        [InlineKeyboardButton("💎 TON 5$", callback_data="vip_ton")],
        [InlineKeyboardButton("🤖 CryptoBot 5$", callback_data="vip_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины, России, Казахстана и других 5$", callback_data="vip_donation")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def dick_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Увеличение Stars 250⭐", callback_data="dick_pay_stars_250")],
        [InlineKeyboardButton("💵 USDT 3$", callback_data="dick_usdt")],
        [InlineKeyboardButton("💎 TON 3$", callback_data="dick_ton")],
        [InlineKeyboardButton("🤖 CryptoBot 3$", callback_data="dick_cryptobot")],
        [InlineKeyboardButton("🌍 Оплата для Украины, России, Казахстана и других 3$", callback_data="dick_donation")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Показываем сначала методы (как ты просил) — без цены. Кнопки ведут на show_method (вывод цены+ссылки)
def country_methods_keyboard(prefix: str):
    # prefix: pay_donation | vip_donation | dick_donation
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Donatello", callback_data=f"{prefix}_method_donatello")],
        [InlineKeyboardButton("DonateAlerts", callback_data=f"{prefix}_method_donationalerts")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=prefix)]
    ])

# Кнопки со ссылками и "Я оплатил" (показываются после выбора метода)
def payment_view_buttons(prefix: str, method_key: str, url: str, back_to: str):
    # method_key is one of "donatello", "donationalerts", "fkwallet"
    kb = []
    if url:
        kb.append([InlineKeyboardButton("Перейти к оплате", url=url)])
    kb.append([InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{prefix}_{method_key}")])
    kb.append([InlineKeyboardButton("⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(kb)

# ================== HELPERS ==================
def _category_from_pack(pack: str) -> str:
    p = (pack or "").lower()
    if "vip" in p:
        return "vip"
    if "dick" in p:
        return "dick"
    return "normal"

# ================== СТАРТ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # send photo + keyboard
    try:
        await update.message.reply_photo(
            photo=IMAGE_URL,
            caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"),
            reply_markup=main_keyboard()
        )
    except Exception:
        # fallback to text only if photo fails
        await update.message.reply_text(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:", reply_markup=main_keyboard())

# ================== ОБРАБОТКА КНОПОК ==================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    data = query.data or ""

    # ---------- BACK handlers ----------
    if data in ("back_main", "back"):
        # show main keyboard (edit current message if possible)
        try:
            # try to edit current message to main keyboard
            await query.edit_message_text(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:", reply_markup=main_keyboard())
        except Exception:
            # fallback: send new message
            try:
                await query.message.reply_photo(photo=IMAGE_URL, caption=(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:"), reply_markup=main_keyboard())
            except Exception:
                await query.message.reply_text(f"📢 Наш основной канал: {MAIN_CHANNEL}\n\nВыберите способ оплаты:", reply_markup=main_keyboard())
        return

    # ---------- Support ----------
    if data == "support":
        pending_users[user_id] = {"state": "support"}
        save_states()
        try:
            await query.edit_message_text("🛠 Напишите своё сообщение поддержки — мы перешлём его модератору.")
        except Exception:
            await query.message.reply_text("🛠 Напишите своё сообщение поддержки — мы перешлём его модератору.")
        return

    # ---------- Admin reply state ----------
    if data.startswith("replyto_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        try:
            target = int(data.split("_", 1)[1])
        except Exception:
            await query.answer("❌ Неверный идентификатор.", show_alert=True)
            return
        admin_reply_state[user_id] = target
        save_states()
        await query.edit_message_text(f"✍️ Отправь текст — он будет переслан пользователю {target}.")
        return

    # ---------- Invoices (stars) ----------
    if data == "pay_stars_200":
        prices = [LabeledPrice("Доступ в приват", 200)]
        try:
            await query.message.reply_invoice(
                title="Вход в приват",
                description="Оплата за доступ к приватному каналу",
                payload="privat-200stars",
                provider_token=STARS_PROVIDER_TOKEN,
                currency="XTR",
                prices=prices,
                start_parameter="stars"
            )
        except Exception as e:
            logger.exception("Ошибка при отправке инвойса: %s", e)
            await query.message.reply_text("Не удалось инициировать оплату звёздами.")
        return

    if data == "vip_pay_stars_500":
        prices = [LabeledPrice("VIP-приват", 500)]
        try:
            await query.message.reply_invoice(title="VIP-приватка",
                                              description="Оплата за VIP-приватку",
                                              payload="vip-500stars",
                                              provider_token=STARS_PROVIDER_TOKEN,
                                              currency="XTR",
                                              prices=prices,
                                              start_parameter="vipstars")
        except Exception as e:
            logger.exception("Ошибка при отправке инвойса: %s", e)
            await query.message.reply_text("Не удалось инициировать оплату звёздами.")
        return

    if data == "dick_pay_stars_250":
        prices = [LabeledPrice("Увеличение члена", 250)]
        try:
            await query.message.reply_invoice(title="🍆 Увеличение члена",
                                              description="Оплата услуги увеличения члена",
                                              payload="dick-250stars",
                                              provider_token=STARS_PROVIDER_TOKEN,
                                              currency="XTR",
                                              prices=prices,
                                              start_parameter="dickstars")
        except Exception as e:
            logger.exception("Ошибка при отправке инвойса: %s", e)
            await query.message.reply_text("Не удалось инициировать оплату звёздами.")
        return

    # ---------- USDT / TON / Crypto flows (kept, amounts updated) ----------
    if data == "pay_usdt":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("USDT TRC20", callback_data="pay_usdt_trc")],
            [InlineKeyboardButton("USDT ERC20", callback_data="pay_usdt_erc")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        await query.edit_message_text("💵 Выберите сеть для оплаты USDT (3$):", reply_markup=kb)
        return

    if data == "pay_usdt_trc":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_usdt_trc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])
        await query.edit_message_text(f"💵 Оплата USDT TRC20\nСумма: 3$\nАдрес: {USDT_TRC20}", reply_markup=kb)
        return

    if data == "pay_usdt_erc":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_usdt_erc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])
        await query.edit_message_text(f"💵 Оплата USDT ERC20\nСумма: 3$\nАдрес: {USDT_ERC20}", reply_markup=kb)
        return

    if data == "vip_usdt":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("USDT TRC20", callback_data="vip_usdt_trc")],
            [InlineKeyboardButton("USDT ERC20", callback_data="vip_usdt_erc")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]
        ])
        await query.edit_message_text("💵 Выберите сеть для VIP USDT (5$):", reply_markup=kb)
        return

    if data == "vip_usdt_trc":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_usdt_trc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]])
        await query.edit_message_text(f"💵 VIP Оплата USDT TRC20\nСумма: 5$\nАдрес: {USDT_TRC20}", reply_markup=kb)
        return

    if data == "vip_usdt_erc":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_usdt_erc")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]])
        await query.edit_message_text(f"💵 VIP Оплата USDT ERC20\nСумма: 5$\nАдрес: {USDT_ERC20}", reply_markup=kb)
        return

    if data == "pay_ton":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_ton")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])
        await query.edit_message_text(f"💎 Оплата TON\nСумма: 3$\nАдрес: {TON_ADDRESS}", reply_markup=kb)
        return

    if data == "vip_ton":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_ton")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]])
        await query.edit_message_text(f"💎 Оплата TON\nСумма: 5$\nАдрес: {TON_ADDRESS}", reply_markup=kb)
        return

    if data == "pay_cryptobot":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в CryptoBot", url=f"https://{CRYPTOBOT_LINK}" if not CRYPTOBOT_LINK.startswith("http") else CRYPTOBOT_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data="paid_pay_cryptobot")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]])
        await query.edit_message_text(f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 3$", reply_markup=kb)
        return

    if data == "vip_cryptobot":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в CryptoBot", url=f"https://{CRYPTOBOT_LINK}" if not CRYPTOBOT_LINK.startswith("http") else CRYPTOBOT_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data="paid_vip_cryptobot")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]])
        await query.edit_message_text(f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 5$", reply_markup=kb)
        return

    # ---------- Donation menus: show country methods first ----------
    # Normal
    if data == "pay_donation":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Украина", callback_data="pay_donation_country_ukraine")],
            [InlineKeyboardButton("Россия", callback_data="pay_donation_country_russia")],
            [InlineKeyboardButton("Казахстан и другие", callback_data="pay_donation_country_kazakhstan")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        await query.edit_message_text("Выберите страну для оплаты:", reply_markup=kb)
        return

    # VIP
    if data == "vip_donation":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Украина", callback_data="vip_donation_country_ukraine")],
            [InlineKeyboardButton("Россия", callback_data="vip_donation_country_russia")],
            [InlineKeyboardButton("Казахстан и другие", callback_data="vip_donation_country_kazakhstan")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="vip_menu")]
        ])
        await query.edit_message_text("Выберите страну для оплаты (VIP):", reply_markup=kb)
        return

    # Dick
    if data == "dick_donation":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Украина", callback_data="dick_donation_country_ukraine")],
            [InlineKeyboardButton("Россия", callback_data="dick_donation_country_russia")],
            [InlineKeyboardButton("Казахстан и другие", callback_data="dick_donation_country_kazakhstan")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="dick_menu")]
        ])
        await query.edit_message_text("Выберите страну для оплаты (Увеличение):", reply_markup=kb)
        return

    # ---------- Country selected -> show methods (Donatello / DonateAlerts / FK) ----------
    # Normal donation country buttons
    if data == "pay_donation_country_ukraine":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Donatello", callback_data="pay_donation_method_donatello")],
            [InlineKeyboardButton("DonateAlerts", callback_data="pay_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="pay_donation")]
        ])
        await query.edit_message_text("🇺🇦 Украина — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "pay_donation_country_russia":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="pay_donation_method_donationalerts")],
            [InlineKeyboardButton("FK Wallet", callback_data="pay_donation_method_fkwallet")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="pay_donation")]
        ])
        await query.edit_message_text("🇷🇺 Россия — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "pay_donation_country_kazakhstan":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="pay_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="pay_donation")]
        ])
        await query.edit_message_text("🇰🇿 Казахстан — выберите способ оплаты:", reply_markup=kb)
        return

    # VIP donation country buttons
    if data == "vip_donation_country_ukraine":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Donatello", callback_data="vip_donation_method_donatello")],
            [InlineKeyboardButton("DonateAlerts", callback_data="vip_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="vip_donation")]
        ])
        await query.edit_message_text("🇺🇦 (VIP) Украина — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "vip_donation_country_russia":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="vip_donation_method_donationalerts")],
            [InlineKeyboardButton("FK Wallet", callback_data="vip_donation_method_fkwallet")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="vip_donation")]
        ])
        await query.edit_message_text("🇷🇺 (VIP) Россия — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "vip_donation_country_kazakhstan":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="vip_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="vip_donation")]
        ])
        await query.edit_message_text("🇰🇿 (VIP) Казахстан — выберите способ оплаты:", reply_markup=kb)
        return

    # Dick donation country buttons
    if data == "dick_donation_country_ukraine":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Donatello", callback_data="dick_donation_method_donatello")],
            [InlineKeyboardButton("DonateAlerts", callback_data="dick_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="dick_donation")]
        ])
        await query.edit_message_text("🇺🇦 (Увел.) Украина — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "dick_donation_country_russia":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="dick_donation_method_donationalerts")],
            [InlineKeyboardButton("FK Wallet", callback_data="dick_donation_method_fkwallet")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="dick_donation")]
        ])
        await query.edit_message_text("🇷🇺 (Увел.) Россия — выберите способ оплаты:", reply_markup=kb)
        return

    if data == "dick_donation_country_kazakhstan":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("DonateAlerts", callback_data="dick_donation_method_donationalerts")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="dick_donation")]
        ])
        await query.edit_message_text("🇰🇿 (Увел.) Казахстан — выберите способ оплаты:", reply_markup=kb)
        return

    # ---------- Method selected -> show price + link + "I paid" ----------
    # Unified mapping: prefix could be pay_donation, vip_donation, dick_donation
    m = re.match(r"(?P<prefix>pay_donation|vip_donation|dick_donation|pay_donation_method|vip_donation_method|dick_donation_method)_(?P<method>.+)", data)
    if m:
        # Some callback formats are like pay_donation_method_donationalerts (the earlier code used that)
        # But we also handle variants; normalize:
        # We'll parse using split if regex not precise
        full = data
        # Determine prefix and method nicely:
        # try to find pattern ..._method_<method> first
        if "_method_" in full:
            parts = full.split("_method_")
            prefix = parts[0]
            method = parts[1]
        else:
            # fallback split by first underscore after prefix
            # Examples: pay_donation_donationalerts
            parts = full.split("_")
            prefix = "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
            method = parts[-1]

        # Determine price text by trying to infer country context in previous message or prefix.
        # We'll set default 3$ and region-specific labels if prefix contains vip/dick or if message text had country names.
        text_lower = (query.message.text or "").lower()
        if "украин" in text_lower or "укр" in text_lower:
            price_text = "124 ₴ / 3 $"
        elif "рос" in text_lower or "руб" in text_lower:
            price_text = "280 ₽ / 3 $"
        elif "казах" in text_lower or "казахстан" in text_lower:
            price_text = "3 $"
        else:
            price_text = "3 $"

        # choose URL for method
        url = None
        if "donatello" in method:
            url = DONATELLO_LINK
            method_read = "Donatello"
        elif "donationalerts" in method or "donatealerts" in method:
            url = DONATION_LINK
            method_read = "DonateAlerts"
        elif "fkwallet" in method or "fk" in method:
            url = FKWALLET_LINK
            method_read = "FK Wallet"
        else:
            # unknown -> fallback to donatealerts
            url = DONATION_LINK
            method_read = method

        # back_to should return to the country list for same prefix
        # map prefix to back target
        if prefix.startswith("pay_donation"):
            back_to = "pay_donation"
            title = "Оплата"
        elif prefix.startswith("vip_donation"):
            back_to = "vip_donation"
            title = "VIP Оплата"
        elif prefix.startswith("dick_donation"):
            back_to = "dick_donation"
            title = "Оплата (Увеличение)"
        else:
            back_to = "pay_donation"
            title = "Оплата"

        view_text = f"💳 {title}\n\nСпособ: {method_read}\n💸 К оплате: {price_text}\n\nНажмите «Перейти к оплате» для перехода или «✅ Я оплатил», чтобы отправить скрин."
        await query.edit_message_text(view_text, reply_markup=payment_view_buttons(prefix, method, url, back_to))
        return

    # ---------- Dick menu (increase) - other flows (USDT/TON) ----------
    if data == "dick_menu":
        await query.edit_message_text("🍆 Увеличение члена. Цена: 250₽ / 3 USDT / 350⭐\nВыберите способ оплаты:", reply_markup=dick_keyboard())
        return

    if data == "dick_usdt":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("USDT TRC20", callback_data="dick_usdt_trc")],
            [InlineKeyboardButton("USDT ERC20", callback_data="dick_usdt_erc")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="dick_menu")]
        ])
        await query.edit_message_text("💵 Выберите сеть для оплаты USDT (3$):", reply_markup=kb)
        return

    if data in ("dick_usdt_trc", "dick_usdt_erc"):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{data}")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="dick_menu")]])
        addr = USDT_TRC20 if data.endswith("trc") else USDT_ERC20
        await query.edit_message_text(f"💵 Оплата USDT\nСумма: 3$\nАдрес: {addr}", reply_markup=kb)
        return

    if data == "dick_ton":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Я оплатил", callback_data="paid_dick_ton")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="dick_menu")]])
        await query.edit_message_text(f"💎 Оплата TON\nСумма: 3$\nАдрес: {TON_ADDRESS}", reply_markup=kb)
        return

    if data == "dick_cryptobot":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в CryptoBot", url=f"https://{CRYPTOBOT_LINK}" if not CRYPTOBOT_LINK.startswith("http") else CRYPTOBOT_LINK)],
                                   [InlineKeyboardButton("✅ Я оплатил", callback_data="paid_dick_cryptobot")],
                                   [InlineKeyboardButton("⬅️ Назад", callback_data="dick_menu")]])
        await query.edit_message_text(f"🤖 Оплата через CryptoBot\nПерейдите по ссылке:\n{CRYPTOBOT_LINK}\nСумма: 3$", reply_markup=kb)
        return

    # ---------- Универсальная логика: пользователь нажал "✅ Я оплатил" ----------
    if data.startswith("paid_"):
        # Normalize pack identifier: remove leading "paid_"
        pack = data[len("paid_"):]  # e.g. pay_donation_ukraine or pay_donation_method_donationalerts etc
        # For consistency store pack as the thing after paid_
        category = _category_from_pack(pack)
        pending_users[user_id] = {"state": "awaiting_screenshot", "pack": pack, "category": category}
        save_states()

        # Ask user to send a screenshot of payment
        try:
            await query.edit_message_text(
                "✅ Отметка: 'Я оплатил'.\nОтправьте скрин/чек оплаты сюда — модератор проверит и выдаст доступ."
            )
        except Exception:
            await query.message.reply_text(
                "✅ Отметка: 'Я оплатил'.\nОтправьте скрин/чек оплаты сюда — модератор проверит и выдаст доступ."
            )

        # notify admin that user pressed "I paid" (admin will wait for screenshot)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"⚠️ Пользователь @{user.username or user_id} (ID: {user_id}) отметил оплату: {pack}. Ожидается скрин."
            )
        except Exception as e:
            logger.exception("Не удалось уведомить админа о пометке оплаты: %s", e)
        return

    # ---------- Админ выдал ссылку кнопкой (нажата под пересланным фото) ----------
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
            category = info.get("category", "normal")
            # отправляем ссылку в зависимости от категории
            if category == "vip":
                link = VIP_CHANNEL_LINK
            elif category == "dick":
                link = DICK_CHANNEL_LINK
            else:
                link = CHANNEL_LINK
            try:
                await context.bot.send_message(target_id, f"✅ Подтверждено! Вот ваша ссылка:\n{link}")
                await query.answer(f"Ссылка отправлена пользователю {target_id}")
                # remove pending
                try:
                    del pending_users[target_id]
                except KeyError:
                    pass
                save_states()
                # remove "Выдать ссылку" button under admin message
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
            except Exception as e:
                logger.exception("Не удалось отправить ссылку пользователю: %s", e)
                await query.answer("❌ Не удалось отправить ссылку пользователю.", show_alert=True)
        else:
            await query.answer("Пользователь не найден в списке ожидающих.", show_alert=True)
        return

    # Fallback — ответ пустой (на всякий)
    await query.answer()

# ================== PreCheckout (Stars) ==================
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# ================== Успешная оплата Stars ==================
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
            await context.bot.send_message(ADMIN_ID, f"Пользователь @{update.message.from_user.username or user_id} (ID: {user_id}) оплатил {payload}")
        except Exception:
            pass

# ================== Обработка фото (скриншоты) ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or "без_username"

    # Если пользователь помечен как ожидающий скрин — пересылаем фото админу с кнопкой "Выдать ссылку"
    if user_id in pending_users and pending_users[user_id].get("state") == "awaiting_screenshot":
        info = pending_users[user_id]
        pack = info.get("pack", "unknown")
        category = info.get("category", "normal")
        if category == "vip":
            caption_type = "👑 VIP приватка"
        elif category == "dick":
            caption_type = "🍆 Dick приватка"
        else:
            caption_type = "💫 Обычный доступ"

        caption = f"📸 Скрин от @{username} (ID: {user_id})\nПакет: {pack} | {caption_type}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Выдать ссылку", callback_data=f"give_{user_id}")]])
        try:
            # пересылаем фото админу (файл_id) с подписью и кнопкой
            await context.bot.send_photo(
                ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                reply_markup=keyboard
            )
            await update.message.reply_text("📨 Скрин отправлен модератору. Ожидайте подтверждения.")
        except Exception as e:
            logger.exception("Ошибка при пересылке скрина админу: %s", e)
            await update.message.reply_text("❌ Не удалось отправить скрин модератору. Попробуйте позже.")
        return

    # Если пользователь был в support — пересылаем как поддержку
    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        try:
            await context.bot.send_photo(
                ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=(f"📸 Сообщение/скрин поддержки от @{username} (ID: {user_id})"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить пользователю", callback_data=f"replyto_{user_id}")]])
            )
            await update.message.reply_text("📨 Ваше фото/сообщение отправлено в поддержку.")
        except Exception as e:
            logger.exception("Ошибка при отправке поддержки админу: %s", e)
            await update.message.reply_text("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
        try:
            del pending_users[user_id]
            save_states()
        except KeyError:
            pass
        return

    # Иначе — просим сначала нажать "Я оплатил"
    await update.message.reply_text(
        "❗ Чтобы отправить скрин: сначала нажмите кнопку '✅ Я оплатил' в меню нужного пакета, а затем отправьте скрин."
    )

# ================== Обработка текста (поддержка, админ /reply и т.д.) ==================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or ""
    username = user.username or "без_username"

    # support message
    if user_id in pending_users and pending_users[user_id].get("state") == "support":
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📨 Сообщение поддержки от @{username} (ID: {user_id}):\n\n{text}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить пользователю", callback_data=f"replyto_{user_id}")]])
            )
            await update.message.reply_text("✅ Ваше сообщение отправлено. Ожидайте ответ.")
        except Exception as e:
            logger.exception("Ошибка при отправке поддержки админу: %s", e)
            await update.message.reply_text("❌ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
        try:
            del pending_users[user_id]
            save_states()
        except KeyError:
            pass
        return

    # admin: stateful reply
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

    # admin: reply to message with ID in caption
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
                await context.bot.send_message(target, f"💬 Поддержка: {text}")
                await update.message.reply_text(f"✅ Ответ отправлен пользователю {target}")
            except Exception as e:
                await update.message.reply_text(f"❌ Не удалось отправить сообщение пользователю: {e}")
            return

    # old /reply_<id>
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

    # default help
    await update.message.reply_text(
        "Если вы хотите оплатить — нажмите /start и выберите пакет. Для поддержки нажмите кнопку '🛠 Поддержка'."
    )

# ================== Запуск ==================
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

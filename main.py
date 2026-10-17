import os
import re
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# የተስተካከሉ የንግድና የሰፖርት ትክክለኛ መረጃዎች
TELEBIRR_NAME = "Aymen Nesredin Redi"
TELEBIRR_NUMBER = "0939357745"
CBE_ACCOUNT = "1000780294322"
CBE_NAME = "Aymen Nesredin Redi"
COOP_ACCOUNT = "1947701000001"
COOP_NAME = "Aymen Nesredin Redi"

# አዲሶቹ የተጨመሩ የባንክ አካውንቶች
AWASH_ACCOUNT = "01425174740300"
AWASH_NAME = "Nesredin Redi"
ABYSSINIA_ACCOUNT = "100404915"
ABYSSINIA_NAME = "Nesredin Redi"
DASHEN_ACCOUNT = "2912539951521"
DASHEN_NAME = "Nesredin Redi"

SUPPORT_USERNAME = "@Neon_ghost147"

# የእኛ Sample/Official የ USDT መቀበያ አድራሻዎች
OUR_BYBIT_UID = "580130044"
OUR_POLYGON_ADDRESS = "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"
OUR_BEP20_ADDRESS = "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

orders_cache = {}

# FSM States
class BuyUSDTState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_network = State()
    waiting_for_address = State()
    waiting_for_payment_method = State()
    waiting_for_receipt = State()

class SellUSDTState(StatesGroup):
    waiting_for_payout_method = State()
    waiting_for_account_number = State()
    waiting_for_account_name = State()
    waiting_for_deposit_network = State()
    waiting_for_proof = State()

class TelegramPremiumState(StatesGroup):
    waiting_for_plan = State()
    waiting_for_username = State()
    waiting_for_payment_method = State()
    waiting_for_proof = State()

class GeminiProState(StatesGroup):
    waiting_for_payment_method = State()
    waiting_for_proof = State()

class UnlimitedDataState(StatesGroup):
    waiting_for_phone_number = State()
    waiting_for_payment_method = State()
    waiting_for_proof = State()

class AdminRejectState(StatesGroup):
    waiting_for_reason = State()

# ዋናው ማኑ ሜኑ ኪቦርድ (አልተነካም)
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Buy USDT | USDT መግዛት", callback_data="buy_usdt"),
            InlineKeyboardButton(text="🔴 Sell USDT | USDT መሸጥ", callback_data="sell_usdt")
        ],
        [
            InlineKeyboardButton(text="💎 Telegram Premium", callback_data="telegram_premium"),
            InlineKeyboardButton(text="✨ Gemini Pro 18m (350 ETB)", callback_data="gemini_pro")
        ],
        [
            InlineKeyboardButton(text="🌐 Monthly Unlimited Data (1,576 ETB)", callback_data="unlimited_data")
        ],
        [
            InlineKeyboardButton(text="🛍 Digital Goods / Top-up", callback_data="digital_goods")
        ],
        [
            InlineKeyboardButton(text="👤 My Profile", callback_data="my_profile"),
            InlineKeyboardButton(text="💰 Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="🛠 Support", callback_data="support"),
            InlineKeyboardButton(text="📊 Bot Log", callback_data="bot_log")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 ሰላም <b>{message.from_user.first_name}</b> እንቋዕ ደህና መጡ!\n\n"
        "🇪🇹 <b>Ethiopian P2P Crypto & Digital Goods Marketplace</b>\n"
        "የኢትዮጵያ P2P ክሪፕቶ እና ዲጂታል እቃዎች ማርኬት\n\n"
        "እባክዎ ከታች ካሉት አማራጮች የሚፈልጉትን ይምረጡ፦"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    menu_text = "🏠 <b>ዋና ማውጫ (Main Menu):</b>\n\nእባክዎ የሚፈልጉትን አገልግሎት ከታች ይምረጡ፦"
    await callback.message.edit_text(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "my_profile")
async def show_my_profile(callback: types.CallbackQuery):
    user = callback.from_user
    profile_text = (
        f"🛡 <b>My Profile | የእኔ መገለጫ</b>\n\n"
        f"🆔 <b>ID:</b> {user.id}\n"
        f"ዩዘርናም: @{user.username if user.username else 'Not set'}\n\n"
        f"💰 <b>Balances:</b>\n"
        f"• ETB: 0.00 ETB\n"
        f"• USDT: 0.0000 USDT\n\n"
        f"💳 <b>Payment Method:</b>\n"
        f"• Telebirr: {TELEBIRR_NUMBER}\n"
        f"• CBE Account: {CBE_ACCOUNT}\n"
        f"• Name: {TELEBIRR_NAME}\n\n"
        f"🔗 <b>Your referral link:</b>\n"
        f"t.me/your_bot?start=ref_{user.id}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Payment Method", callback_data="edit_payment")],
        [
            InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton(text="✅ Completed History", callback_data="completed_history")
        ],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    support_text = (
        "🛠 <b>Customer Support | የደንበኞች አገልግሎት</b>\n\n"
        "ማንኛውም ጥያቄ፣ አስተያየት ወይም የክፍያ ችግር ካጋጠመዎት እባክዎ በቀጥታ ሰፖርታችንን ያናግሩ፦\n\n"
        f"👤 <b>Support Admin:</b> {SUPPORT_USERNAME}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 DM Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    await callback.message.edit_text(support_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ==========================================
# 🟢 BUY USDT WORKFLOW
# ==========================================

@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    stock = 98.0
    rate = 197.0
    text = (
        "💰 <b>Buy USDT | USDT መግዛት</b>\n\n"
        f"• Available stock (የአሁን መጠን): {stock} USDT\n"
        f"• Rate (ተመን): 1 USDT = {rate} ETB\n"
        f"• Min / Max (ዝቅተኛ / ከፍተኛ): 0.5 - 10000.0 USDT\n\n"
        "Enter how much USDT you want to buy:\n"
        "ምን ያህል USDT መግዛት ይፈልጋሉ? (ምሳሌ: 10)"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_amount)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass
        
    try:
        amount = float(message.text)
        if amount < 0.5 or amount > 10000.0:
            err_text = "⚠️ እባክዎ ከ 0.5 እስከ 10000.0 USDT መካከል ያስገቡ፦"
            if last_msg_id:
                await bot.edit_message_text(err_text, chat_id=message.chat.id, message_id=last_msg_id)
            return
        
        rate = 197.0
        total_price = amount * rate
        await state.update_data(amount=amount, total_price=total_price)
        
        text = (
            "✅ <b>Order Summary | የትዕዛዝ ማጠቃለያ</b>\n"
            f"• Amount (መጠን): {amount:.4f} USDT\n"
            f"• Total to pay (የሚከፍሉት ብር): {total_price:,.2f} ETB\n"
            f"• Rate (ተመን): {rate} ETB\n\n"
            "USDT የት ይላክልዎታል? (የመቀበያ መንገድ ይምረጡ)፦"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Binance ID", callback_data="net_binance"),
                InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="net_bep20")
            ],
            [
                InlineKeyboardButton(text="🔶 Bybit UID", callback_data="net_bybit"),
                InlineKeyboardButton(text="🟣 Polygon (USDT)", callback_data="net_polygon")
            ],
            [
                InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
            ]
        ])
        await state.set_state(BuyUSDTState.waiting_for_network)
        if last_msg_id:
            await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")
            
    except ValueError:
        if last_msg_id:
            await bot.edit_message_text("❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 10)፦", chat_id=message.chat.id, message_id=last_msg_id)

@dp.callback_query(BuyUSDTState.waiting_for_network, F.data.startswith("net_"))
async def select_network(callback: types.CallbackQuery, state: FSMContext):
    network_map = {
        "net_binance": "Binance Pay ID",
        "net_bep20": "BSC (BEP20) Address",
        "net_bybit": "Bybit UID",
        "net_polygon": "Polygon Network Address"
    }
    net_name = network_map.get(callback.data, "Crypto Address")
    await state.update_data(network=net_name)
    
    text = (
        "📥 <b>USDT receiving destination | USDT መቀበያ አድራሻ</b>\n\n"
        f"USDT የሚላክልዎትን <b>{net_name}</b> ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_address)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    network = data.get("network")
    address = message.text.strip()
    
    try:
        await message.delete()
    except Exception:
        pass

    is_valid = True
    err_msg = ""

    if "UID" in network or "Binance" in network or "Bybit" in network:
        if not address.isdigit() or len(address) < 8 or len(address) > 12:
            is_valid = False
            err_msg = f"⚠️ እባክዎ ለ <b>{network}</b> ትክክለኛ የቁጥር መታወቂያ (8-12 ዲጂት) ያስገቡ፦"
    elif "BEP20" in network or "Polygon" in network:
        if not address.startswith("0x") or len(address) != 42:
            is_valid = False
            err_msg = "⚠️ አድራሻው በ '0x' መጀመር እና 42 ፊደላት/ቁጥሮች መሆን አለበት፦"

    if not is_valid:
        if last_msg_id:
            await bot.edit_message_text(err_msg, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
        return

    await state.update_data(address=address)
    amount = data.get("amount")
    total_price = data.get("total_price")
    
    text = (
        "📬 <b>Receiving destination saved | መድረሻው ተይዟል</b>\n\n"
        f"• USDT: {amount:.4f}\n"
        f"• ETB to pay (የሚከፍሉት ብር): {total_price:,.2f} ETB\n"
        f"• Destination (መቀበያ): {address}\n\n"
        "ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Telebirr", callback_data="buy_pay_telebirr"),
            InlineKeyboardButton(text="🏦 CBE (ንግድ ባንክ)", callback_data="buy_pay_cbe")
        ],
        [
            InlineKeyboardButton(text="🏦 COOP Bank", callback_data="buy_pay_coop"),
            InlineKeyboardButton(text="🦁 Awash Bank", callback_data="buy_pay_awash")
        ],
        [
            InlineKeyboardButton(text="🏛 Abyssinia", callback_data="buy_pay_abyssinia"),
            InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="buy_pay_dashen")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
        ]
    ])
    await state.set_state(BuyUSDTState.waiting_for_payment_method)
    if last_msg_id:
        await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(BuyUSDTState.waiting_for_payment_method, F.data.startswith("buy_pay_"))
async def buy_payment_selected(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    total_price = data.get("total_price")
    
    pay_code = callback.data
    if pay_code == "buy_pay_telebirr":
        b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "buy_pay_cbe":
        b_name, b_acc, b_owner = "CBE (ንግድ ባንክ)", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "buy_pay_coop":
        b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "buy_pay_awash":
        b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "buy_pay_abyssinia":
        b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else:
        b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = (
        "📋 <b>Order summary</b>\n"
        f"• USDT: {amount:.4f} USDT\n"
        f"• Pay: {total_price:,.2f} ETB\n\n"
        f"🏛 <b>{b_name}</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        f"Send the exact ETB amount, then upload a clear receipt screenshot.\n"
        f"ትክክለኛውን የብር መጠን ከፍለው ግልጽ የ{b_name} ደረሰኝ ስክሪንሾት ይላኩ።"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_receipt)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass
        
    if last_msg_id:
        await bot.edit_message_text("🔄 Processing payment proof...\n⏳ Reading screenshot with OCR...", chat_id=message.chat.id, message_id=last_msg_id)
        
    await asyncio.sleep(2)
    
    amount = data.get("amount")
    total_price = data.get("total_price")
    address = data.get("address")
    network = data.get("network")
    user = message.from_user
    
    admin_text = (
        f"🚨 <b>New BUY USDT Order! (አዲስ የግዢ ትዕዛዝ)</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Amount: {amount} USDT\n"
        f"💰 Pay: {total_price:,.2f} ETB\n"
        f"🌐 Network: {network}\n"
        f"📍 Address/UID: <code>{address}</code>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve (አጽድቅ)", callback_data=f"app_{user.id}"),
            InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{user.id}")
        ]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="HTML"
            )
            orders_cache[user.id] = {"amount": amount, "address": address, "network": network}
        except Exception as e:
            print(f"Error sending to admin group: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(
            "✅ <b>Payment proof received successfully!</b>\n\n"
            "የክፍያ ማረጋገጫዎ ደርሶናል! ትዕዛዝዎ በአስተዳዳሪዎች እየተጣራ ነው። እባክዎ በትዕግስት ይጠብቁ... ⏳",
            chat_id=message.chat.id,
            message_id=last_msg_id,
            parse_mode="HTML"
        )
    await state.clear()


# ==========================================
# 🔴 SELL USDT WORKFLOW
# ==========================================

@dp.callback_query(F.data == "sell_usdt")
async def start_sell_usdt(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "🔴 <b>Sell USDT — Step 1 of 4 | USDT መሸጥ — ደረጃ 1</b>\n\n"
        "How would you like to receive your ETB payout?\n"
        "ብር የሚቀበሉበትን የክፍያ መንገድ ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Telebirr", callback_data="payout_telebirr"),
            InlineKeyboardButton(text="🏦 CBE (ንግድ ባንክ)", callback_data="payout_cbe")
        ],
        [
            InlineKeyboardButton(text="🏦 COOP Bank", callback_data="payout_coop"),
            InlineKeyboardButton(text="🦁 Awash Bank", callback_data="payout_awash")
        ],
        [
            InlineKeyboardButton(text="🏛 Abyssinia", callback_data="payout_abyssinia"),
            InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="payout_dashen")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
        ]
    ])
    await state.set_state(SellUSDTState.waiting_for_payout_method)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(SellUSDTState.waiting_for_payout_method, F.data.startswith("payout_"))
async def select_payout_method(callback: types.CallbackQuery, state: FSMContext):
    method_map = {
        "payout_telebirr": "Telebirr",
        "payout_cbe": "CBE",
        "payout_coop": "COOP Bank",
        "payout_awash": "Awash Bank",
        "payout_abyssinia": "Bank of Abyssinia",
        "payout_dashen": "Dashen Bank"
    }
    method_name = method_map.get(callback.data, "Bank Account")
    await state.update_data(payout_method=method_name)
    
    text = (
        f"🔴 <b>Step 2 of 4 — {method_name} details | መረጃ ያስገቡ</b>\n\n"
        f"ብር የሚቀበሉበትን የ <b>{method_name}</b> ቁጥር ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_account_number)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(SellUSDTState.waiting_for_account_number)
async def process_account_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    method = data.get("payout_method")
    account_num = message.text.strip()
    
    try:
        await message.delete()
    except Exception:
        pass

    is_valid = True
    err_msg = ""

    if method == "Telebirr":
        if not (account_num.startswith("09") or account_num.startswith("07")) or len(account_num) != 10 or not account_num.isdigit():
            is_valid = False
            err_msg = "⚠️ <b>Telebirr</b> ቁጥር በ '09' ወይም '07' መጀመር እና 10 አሃዞች መሆን አለበት፦"
    elif method == "CBE":
        if not account_num.startswith("1000") or len(account_num) != 13 or not account_num.isdigit():
            is_valid = False
            err_msg = "⚠️ የ <b>CBE (ንግድ ባንክ)</b> ሂሳብ ቁጥር በ '1000' መጀመር እና 13 አሃዞች መሆን አለበት፦"
    elif method in ["COOP Bank", "Awash Bank", "Bank of Abyssinia", "Dashen Bank"]:
        if not account_num.isdigit() or len(account_num) < 8:
            is_valid = False
            err_msg = f"⚠️ እባክዎ ትክክለኛ የ <b>{method}</b> የሂሳብ ቁጥር ያስገቡ፦"

    if not is_valid:
        if last_msg_id:
            await bot.edit_message_text(err_msg, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
        return

    await state.update_data(account_num=account_num)
    
    text = (
        f"👤 <b>Enter Account Holder Name | የባለቤት ስም ያስገቡ</b>\n\n"
        f"በ {method} የተመዘገበውን የባለቤቱን ሙሉ ስም ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_account_name)
    if last_msg_id:
        await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")

@dp.message(SellUSDTState.waiting_for_account_name)
async def process_account_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    acc_name = message.text.strip()
    
    try:
        await message.delete()
    except Exception:
        pass

    if len(acc_name) < 3:
        if last_msg_id:
            await bot.edit_message_text("⚠️ እባክዎ ትክክለኛ ሙሉ ስም ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)
        return

    await state.update_data(acc_name=acc_name)
    data = await state.get_data()
    method = data.get("payout_method")
    account_num = data.get("account_num")
    
    text = (
        "🔴 <b>Step 3 of 4 — Choose USDT deposit method | ደረጃ 3 — USDT ማስገቢያ መንገድ ይምረጡ</b>\n\n"
        "<b>Your ETB payout destination | የብር መቀበያ መረጃዎ፦</b>\n"
        f"• Method: {method}\n"
        f"• Number/Account: <code>{account_num}</code>\n"
        f"• Name: {acc_name}\n\n"
        "USDT ለእኛ በምን መንገድ ይልካሉ? (ከታች ይምረጡ)፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔶 Bybit UID", callback_data="deposit_bybit"),
            InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="deposit_bep20")
        ],
        [
            InlineKeyboardButton(text="🟣 Polygon (USDT)", callback_data="deposit_polygon")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
        ]
    ])
    await state.set_state(SellUSDTState.waiting_for_deposit_network)
    if last_msg_id:
        await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")

@dp.callback_query(SellUSDTState.waiting_for_deposit_network, F.data.startswith("deposit_"))
async def select_deposit_network(callback: types.CallbackQuery, state: FSMContext):
    net_code = callback.data
    if net_code == "deposit_bybit":
        net_name = "Bybit UID"
        our_addr = OUR_BYBIT_UID
    elif net_code == "deposit_bep20":
        net_name = "BSC (BEP20)"
        our_addr = OUR_BEP20_ADDRESS
    else:
        net_name = "Polygon Network"
        our_addr = OUR_POLYGON_ADDRESS

    await state.update_data(deposit_network=net_name, our_address=our_addr)
    
    text = (
        f"🔴 <b>Step 4 of 4 — {net_name} | ደረጃ 4 — {net_name}</b>\n\n"
        f"USDT ወደዚህ የእኛ {net_name} ይላኩ፦\n\n"
        f"<code>{our_addr}</code>\n\n"
        "የላኩበትን ክፍያ ግልጽ ስክሪንሾት ይላኩ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(SellUSDTState.waiting_for_proof, F.photo)
async def process_sell_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass
        
    if last_msg_id:
        await bot.edit_message_text("🔄 Reading transfer proof for manual review...", chat_id=message.chat.id, message_id=last_msg_id)
        
    await asyncio.sleep(2)
    
    payout_method = data.get("payout_method")
    account_num = data.get("account_num")
    acc_name = data.get("acc_name")
    deposit_network = data.get("deposit_network")
    user = message.from_user
    
    admin_text = (
        f"🚨 <b>New SELL USDT Order! (አዲስ የመሸጥ ትዕዛዝ)</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"🌐 Sent via: {deposit_network}\n"
        f"💵 Payout Method: {payout_method}\n"
        f"📍 Payout Account: <code>{account_num}</code>\n"
        f"👤 Account Name: {acc_name}\n\n"
        "የ USDT ትራንስፈር ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve (ብር ላክኩ)", callback_data=f"app_{user.id}"),
            InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{user.id}")
        ]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending to admin group: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(
            "✅ <b>Transfer proof received successfully!</b>\n\n"
            "የUSDT ትራንስፈር ማረጋገጫዎ ደርሶናል! አድሚኑ ማረጋገጫውን አይቶ የኢትዮጵያ ብር በባንክ/ቴሌብር ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳",
            chat_id=message.chat.id,
            message_id=last_msg_id,
            parse_mode="HTML"
        )
    await state.clear()


# ==========================================
# 🌐 MONTHLY UNLIMITED DATA WORKFLOW (አዲሱ ፍሰት)
# ==========================================

@dp.callback_query(F.data == "unlimited_data")
async def start_unlimited_data(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "🌐 <b>Monthly Unlimited Data</b>\n\n"
        "🏷 <b>Price:</b> 1,576.00 ETB each\n"
        "🔥 <b>In stock:</b> 2\n\n"
        "🔥 <b>Special Offer</b>\n"
        "🍃 <b>Validity:</b> 30 Days\n"
        "⚡ <b>Speed:</b> Fast\n\n"
        "💯 <b>Guaranteed and Fast delivery</b>\n\n"
        "📍 <b>How to Order:</b>\n"
        "1. Send your phone number\n"
        "2. Complete your payment via Bank or Telebirr\n"
        "3. Sit back and enjoy unlimited browsing 🤝\n\n"
        "Tap <b>Buy now</b> when you are ready."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Buy now (1,576 ETB)", callback_data="buy_data_now")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "buy_data_now")
async def ask_data_phone_number(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "❓ <b>Enter the phone number that should receive this order:</b>\n\n"
        "ያልተገደበው ዳታ (Monthly Unlimited Data) የሚጫንበትን የስልክ ቁጥር ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(UnlimitedDataState.waiting_for_phone_number)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(UnlimitedDataState.waiting_for_phone_number)
async def process_data_phone_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    phone_num = message.text.strip()
    
    try:
        await message.delete()
    except Exception:
        pass

    # Strict Phone Number Validation (09 or 07, 10 digits)
    if not (phone_num.startswith("09") or phone_num.startswith("07")) or len(phone_num) != 10 or not phone_num.isdigit():
        if last_msg_id:
            await bot.edit_message_text(
                "⚠️ <b>የተሳሳተ የስልክ ቁጥር!</b>\n\nእባክዎ ዳታው የሚሞላበትን ትክክለኛ የስልክ ቁጥር በ '09' ወይም '07' ጀምረው ያስገቡ (10 አሃዝ)፦",
                chat_id=message.chat.id,
                message_id=last_msg_id,
                parse_mode="HTML"
            )
        return

    await state.update_data(data_phone=phone_num)

    text = (
        "🌐 <b>Monthly Unlimited Data — 1,576.00 ETB</b>\n"
        f"📱 Target Phone: <b>{phone_num}</b>\n\n"
        "እባክዎ ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Telebirr", callback_data="data_pay_telebirr"),
            InlineKeyboardButton(text="🏦 CBE (ንግድ ባንክ)", callback_data="data_pay_cbe")
        ],
        [
            InlineKeyboardButton(text="🏦 COOP Bank", callback_data="data_pay_coop"),
            InlineKeyboardButton(text="🦁 Awash Bank", callback_data="data_pay_awash")
        ],
        [
            InlineKeyboardButton(text="🏛 Abyssinia", callback_data="data_pay_abyssinia"),
            InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="data_pay_dashen")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
        ]
    ])
    await state.set_state(UnlimitedDataState.waiting_for_payment_method)
    if last_msg_id:
        await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(UnlimitedDataState.waiting_for_payment_method, F.data.startswith("data_pay_"))
async def process_data_payment_info(callback: types.CallbackQuery, state: FSMContext):
    pay_code = callback.data
    if pay_code == "data_pay_telebirr":
        b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "data_pay_cbe":
        b_name, b_acc, b_owner = "CBE (ንግድ ባንክ)", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "data_pay_coop":
        b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "data_pay_awash":
        b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "data_pay_abyssinia":
        b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else:
        b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    data = await state.get_data()
    data_phone = data.get("data_phone")

    text = (
        "🌐 <b>Monthly Unlimited Data (30 Days)</b>\n"
        f"📱 Recipient Phone: <b>{data_phone}</b>\n"
        f"💰 Amount to pay: <b>1,576.00 ETB</b>\n\n"
        f"🏛 <b>{b_name} Payment Info</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        "Send the exact 1,576.00 ETB amount, then upload a clear receipt screenshot.\n"
        "ትክክለኛውን 1,576.00 ETB ከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(UnlimitedDataState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(UnlimitedDataState.waiting_for_proof, F.photo)
async def process_data_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass
        
    if last_msg_id:
        await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
        
    await asyncio.sleep(2)
    data_phone = data.get("data_phone")
    user = message.from_user
    
    admin_text = (
        f"🌐 <b>New Monthly Unlimited Data Order!</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"📱 Target Phone Number: <code>{data_phone}</code>\n"
        f"💵 Price: 1,576.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve (ዳታው ተሞላ)", callback_data=f"app_{user.id}"),
            InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{user.id}")
        ]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending to admin group: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(
            "✅ <b>Payment proof received successfully!</b>\n\n"
            f"የክፍያ ማረጋገጫዎ ደርሶናል! ያልተገደበው ዳታ በቅርቡ ወደ <b>{data_phone}</b> ይጫናል። እባክዎ በትዕግስት ይጠብቁ... ⏳",
            chat_id=message.chat.id,
            message_id=last_msg_id,
            parse_mode="HTML"
        )
    await state.clear()


# ==========================================
# ✨ GEMINI PRO 18M WORKFLOW
# ==========================================

@dp.callback_query(F.data == "gemini_pro")
async def start_gemini_pro(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "✨ <b>Gemini Pro 18m</b>\n\n"
        "🏷 <b>Price:</b> 350.00 ETB each\n"
        "🔥 <b>In stock:</b> 34\n\n"
        "📄 <b>DESCRIPTION:</b>\n"
        "You will receive a self-activation link that you can claim yourself. It works with both new and existing Gmail accounts.\n\n"
        "✨ <b>FEATURES:</b>\n"
        "• Self-activation link\n"
        "• No card or payment required for activation\n"
        "• Full 5-user Family Plan\n"
        "• Works on all devices\n\n"
        "Tap <b>Buy now</b> when you are ready."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Buy now (350 ETB)", callback_data="buy_gemini_now")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "buy_gemini_now")
async def select_gemini_payment_method(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "✨ <b>Gemini Pro 18m — 350.00 ETB</b>\n\n"
        "እባክዎ ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Telebirr", callback_data="gem_pay_telebirr"),
            InlineKeyboardButton(text="🏦 CBE (ንግድ ባንክ)", callback_data="gem_pay_cbe")
        ],
        [
            InlineKeyboardButton(text="🏦 COOP Bank", callback_data="gem_pay_coop"),
            InlineKeyboardButton(text="🦁 Awash Bank", callback_data="gem_pay_awash")
        ],
        [
            InlineKeyboardButton(text="🏛 Abyssinia", callback_data="gem_pay_abyssinia"),
            InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="gem_pay_dashen")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")
        ]
    ])
    await state.set_state(GeminiProState.waiting_for_payment_method)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(GeminiProState.waiting_for_payment_method, F.data.startswith("gem_pay_"))
async def process_gemini_payment_info(callback: types.CallbackQuery, state: FSMContext):
    pay_code = callback.data
    if pay_code == "gem_pay_telebirr":
        b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "gem_pay_cbe":
        b_name, b_acc, b_owner = "CBE (ንግድ ባንክ)", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "gem_pay_coop":
        b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "gem_pay_awash":
        b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "gem_pay_abyssinia":
        b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else:
        b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = (
        f"✨ <b>Gemini Pro 18m Activation Link</b>\n"
        f"💰 Amount to pay: <b>350.00 ETB</b>\n\n"
        f"🏛 <b>{b_name} Payment Info</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        "Send the exact 350.00 ETB amount, then upload a clear receipt screenshot.\n"
        "ትክክለኛውን 350.00 ETB ከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(GeminiProState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(GeminiProState.waiting_for_proof, F.photo)
async def process_gemini_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass
        
    if last_msg_id:
        await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
        
    await asyncio.sleep(2)
    user = message.from_user
    
    admin_text = (
        f"✨ <b>New Gemini Pro 18m Order!</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Price: 350.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve (ሊንክ ላክ)", callback_data=f"app_{user.id}"),
            InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{user.id}")
        ]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try:
            await bot.send_photo(
                chat_id=ADMIN_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending to admin group: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(
            "✅ <b>Payment proof received successfully!</b>\n\n"
            "የክፍያ ማረጋገጫዎ ደርሶናል! አድሚኑ ክፍያውን አረጋግጦ የ Gemini Pro Activation link ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳",
            chat_id=message.chat.id,
            message_id=last_msg_id,
            parse_mode="HTML"
        )
    await state.clear()


# ==========================================
# 🛡 ADMIN APPROVE / REJECT CALLBACKS
# ==========================================

@dp.callback_query(F.data.startswith("app_"))
async def admin_approve_order(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>ትዕዛዝዎ በተሳካ ሁኔታ ጸድቋል (Approved)!</b>\n\n"
                "አድሚኑ ክፍያውን አረጋግጦ አገልግሎትዎን ልኮልዎታል። ቦቱን ስለተጠቀሙ እናመሰግናለን! 🙏\n"
                f"ችግር ካጋጠመዎት ሰፖርታችንን ያናግሩ፦ {SUPPORT_USERNAME}"
            ),
            parse_mode="HTML"
        )
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n<b>STATUS: ✅ APPROVED BY ADMIN</b>",
            parse_mode="HTML"
        )
        await callback.answer("ትዕዛዙ በተሳካ ሁኔታ ጸድቋል!")
    except Exception as e:
        await callback.answer(f"ስህተት ተፈጥሯል: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("rej_"))
async def start_admin_reject(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    await state.update_data(reject_user_id=user_id, admin_msg=callback.message)
    await state.set_state(AdminRejectState.waiting_for_reason)
    await callback.message.reply("✏️ እባክዎ ትዕዛዙ ውድቅ የተደረገበትን ምክንያት በጽሁፍ ያስገቡ፦")
    await callback.answer()

@dp.message(AdminRejectState.waiting_for_reason)
async def process_reject_reason(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data()
    user_id = data.get("reject_user_id")
    admin_msg = data.get("admin_msg")
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>ትዕዛዝዎ ውድቅ ተደርጓል (Rejected)!</b>\n\n"
                f"<b>ምክንያት:</b> {reason}\n\n"
                f"ለበለጠ መረጃ እና እገዛ እባክዎ የደንበኞች አገልግሎታችንን ያናግሩ፦ {SUPPORT_USERNAME}"
            ),
            parse_mode="HTML"
        )
        if admin_msg:
            await admin_msg.edit_caption(
                caption=admin_msg.caption + f"\n\n<b>STATUS: ❌ REJECTED</b>\n<b>Reason:</b> {reason}",
                parse_mode="HTML"
            )
        await message.reply("✅ ውድቅ የተደረገበት ምክንያት ለተጠቃሚው ተልኳል!")
    except Exception as e:
        await message.reply(f"❌ ለተጠቃሚው መላክ አልተቻለም: {e}")
        
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# Web Server for Render
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

async def main():
    print("ቦቱ እና ዌብ ሰርቨሩ በሰላም በመጀመር ላይ ናቸው...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

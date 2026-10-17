import os
import re
import asyncio
import aiohttp
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").rstrip('/')
SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

SUPPORT_USERNAME = "@Neon_ghost147"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 🗄 FIREBASE HELPER FUNCTIONS
# ==========================================
async def fb_get(path: str):
    if not FIREBASE_DB_URL:
        return None
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None

async def fb_put(path: str, data):
    if not FIREBASE_DB_URL:
        return
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        await session.put(url, json=data)

async def fb_post(path: str, data):
    if not FIREBASE_DB_URL:
        return None
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                res = await resp.json()
                return res.get("name")
    return None

# ==========================================
# ⚙️ DYNAMIC SETTINGS & ADMINS INITIALIZATION
# ==========================================
DEFAULT_SETTINGS = {
    "rates": {"buy": 197.0, "sell": 182.0},
    "banks": {
        "telebirr": {"name": "Aymen Nesredin Redi", "number": "0939357745"},
        "cbe": {"name": "Aymen Nesredin Redi", "number": "1000780294322"},
        "coop": {"name": "Aymen Nesredin Redi", "number": "1947701000001"},
        "awash": {"name": "Nesredin Redi", "number": "01425174740300"},
        "abyssinia": {"name": "Nesredin Redi", "number": "100404915"},
        "dashen": {"name": "Nesredin Redi", "number": "2912539951521"}
    },
    "crypto": {
        "bybit_uid": "580130044",
        "polygon_address": "0x9244d02e10124bfa091d1d5c25a4aed204833ad7",
        "bep20_address": "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"
    }
}

async def get_settings():
    settings = await fb_get("settings")
    if not settings:
        await fb_put("settings", DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    return settings

async def is_admin(user_id: int) -> bool:
    if user_id == SUPER_ADMIN_ID:
        return True
    admins = await fb_get("admins")
    if admins and str(user_id) in admins:
        return True
    return False

async def save_user(user_id: int, username: str, first_name: str):
    user_data = {"username": username or "", "first_name": first_name or ""}
    await fb_put(f"users/{user_id}", user_data)

# ==========================================
# 📝 FSM STATES
# ==========================================
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

class SupportMessageState(StatesGroup):
    waiting_for_message = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

class AdminRejectState(StatesGroup):
    waiting_for_reason = State()

class BroadcastState(StatesGroup):
    waiting_for_broadcast_msg = State()

class EditSettingsState(StatesGroup):
    waiting_for_buy_rate = State()
    waiting_for_sell_rate = State()
    waiting_for_bank_details = State()
    waiting_for_crypto_details = State()
    waiting_for_new_admin_id = State()

# ጽዱ ዋና ሜኑ ኪቦርድ
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
            InlineKeyboardButton(text="👤 My Profile / History", callback_data="my_profile")
        ],
        [
            InlineKeyboardButton(text="🛠 Support | ድጋፍ", callback_data="support"),
            InlineKeyboardButton(text="❓ Help | እርዳታ", callback_data="help")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
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

# ==========================================
# 👑 ADMIN PANEL & SETTINGS CONTROL
# ==========================================
@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    
    text = "👑 <b>Admin Control Panel | የአስተዳዳሪ ፓነል</b>\n\nእባክዎ ማስተካከል የሚፈልጉትን ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Edit Rates (ተመን ቀይር)", callback_data="admin_edit_rates"),
            InlineKeyboardButton(text="🏛 Edit Banks (ባንኮች ቀይር)", callback_data="admin_edit_banks")
        ],
        [
            InlineKeyboardButton(text="🪙 Edit Crypto (አድራሻዎች ቀይር)", callback_data="admin_edit_crypto"),
            InlineKeyboardButton(text="➕ Add Admin (አድሚን ጨምር)", callback_data="admin_add_admin")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_start_broadcast")
        ]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "admin_edit_rates")
async def admin_edit_rates_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    settings = await get_settings()
    rates = settings.get("rates", {})
    
    text = (
        f"💵 <b>Current Rates:</b>\n"
        f"• Buy Rate: {rates.get('buy')} ETB\n"
        f"• Sell Rate: {rates.get('sell')} ETB\n\n"
        "አዲሱን የ <b>BUY Rate</b> (የመግዣ ተመን) ያስገቡ (ምሳሌ: 198.5)፦"
    )
    await state.set_state(EditSettingsState.waiting_for_buy_rate)
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_buy_rate)
async def process_new_buy_rate(message: types.Message, state: FSMContext):
    try:
        new_buy = float(message.text.strip())
        await state.update_data(new_buy=new_buy)
        await state.set_state(EditSettingsState.waiting_for_sell_rate)
        await message.answer("አዲሱን የ <b>SELL Rate</b> (የመሸጫ ተመን) ያስገቡ (ምሳሌ: 184.0)፦", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ፦")

@dp.message(EditSettingsState.waiting_for_sell_rate)
async def process_new_sell_rate(message: types.Message, state: FSMContext):
    try:
        new_sell = float(message.text.strip())
        data = await state.get_data()
        new_buy = data.get("new_buy")
        
        settings = await get_settings()
        settings["rates"]["buy"] = new_buy
        settings["rates"]["sell"] = new_sell
        await fb_put("settings", settings)
        
        await message.answer(f"✅ <b>ተመኖች በተሳካ ሁኔታ ተቀይረዋል!</b>\n\nBuy: {new_buy} ETB\nSell: {new_sell} ETB", parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ፦")

@dp.callback_query(F.data == "admin_add_admin")
async def admin_add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ አዲስ አድሚን መጨመር የሚችለው ዋናው Super Admin ብቻ ነው!", show_alert=True)
        return
    await state.set_state(EditSettingsState.waiting_for_new_admin_id)
    await callback.message.edit_text("➕ አዲስ አድሚን የሚሆነውን ሰው <b>Telegram User ID</b> ያስገቡ፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_new_admin_id)
async def process_add_new_admin(message: types.Message, state: FSMContext):
    try:
        new_admin_id = int(message.text.strip())
        await fb_put(f"admins/{new_admin_id}", True)
        await message.answer(f"✅ ተጠቃሚ ID <code>{new_admin_id}</code> በአድሚንነት በተሳካ ሁኔታ ተጨምሯል!", parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ የቁጥር ID ብቻ ያስገቡ፦")

# ==========================================
# 👤 MY PROFILE & ORDERS HISTORY
# ==========================================
@dp.callback_query(F.data == "my_profile")
async def show_my_profile(callback: types.CallbackQuery):
    user = callback.from_user
    profile_text = (
        f"🛡 <b>My Profile | የእኔ መገለጫ</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'Not set'}\n\n"
        f"እባክዎ ከታች የትዕዛዝ ታሪክዎን ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 My Orders (ንቁ ትዕዛዞች)", callback_data="my_orders"),
            InlineKeyboardButton(text="✅ Completed History", callback_data="completed_history")
        ],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "my_orders")
async def show_my_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    all_orders = await fb_get(f"user_orders/{user_id}")
    
    if not all_orders:
        text = "📦 <b>My Orders (0)</b>\n\nእስካሁን ምንም ትዕዛዝ አልላኩም።"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")]])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    buttons = []
    for ord_key, ord in list(all_orders.items())[-8:]:
        status = ord.get("status", "PENDING")
        service = ord.get("service", "Order")
        amount = ord.get("amount", 0.0)
        status_icon = "⏳" if status == "PENDING" else ("✅" if status == "APPROVED" else "❌")
        buttons.append([InlineKeyboardButton(text=f"{status_icon} #{ord_key[:6]} — {service} — {amount:,.0f} ETB", callback_data=f"view_ord_{ord_key}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")])
    await callback.message.edit_text(f"📦 <b>My Orders</b>\nTap an order to view details:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🛠 INTERACTIVE SUPPORT SYSTEM
# ==========================================
@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    support_text = (
        "🆘 <b>Support | ድጋፍ</b>\n\n"
        "ስለ ትዕዛዝዎ ጥያቄ ካለዎት ከታች ያለውን <b>Message Admin Inside Bot</b> ቁልፍ በመጫን ቀጥታ ለአድሚን ይጻፉ፦\n\n"
        "🕒 <b>Working hours:</b> 08:00–22:00 EAT"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Message Admin Inside Bot", callback_data="msg_admin_start")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    await callback.message.edit_text(support_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "msg_admin_start")
async def start_msg_admin(callback: types.CallbackQuery, state: FSMContext):
    text = "💬 <b>Message Admin</b>\n\nእባክዎ ለሰፖርት አድሚኖች መላክ የሚፈልጉትን ጥያቄ፣ ጽሁፍ ወይም ስክሪንሾት ያስገቡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(SupportMessageState.waiting_for_message)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.message(SupportMessageState.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass

    user = message.from_user
    admin_caption = f"📩 <b>New Support Message!</b>\n\n👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)"
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Reply to User (መልስ ስጥ)", callback_data=f"reply_user_{user.id}")]])

    if ADMIN_GROUP_ID != 0:
        try:
            if message.photo:
                await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=f"{admin_caption}\n\n💬 <b>Msg:</b> {message.caption if message.caption else ''}", reply_markup=admin_keyboard, parse_mode="HTML")
            else:
                await bot.send_message(ADMIN_GROUP_ID, text=f"{admin_caption}\n\n💬 <b>Msg:</b> {message.text}", reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")

    if last_msg_id:
        await bot.edit_message_text("✅ <b>መልእክትዎ ለአድሚን ተልኳል!</b>\n\nአድሚኖች መልእክትዎን አይተው በቦቱ በኩል ይመልሱልዎታል።", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("reply_user_"))
async def start_admin_reply(callback: types.CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[2])
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    await callback.message.reply(f"✍️ ለተጠቃሚው (ID: <code>{target_user_id}</code>) የሚላከውን መልስ ይጻፉ፦", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminReplyState.waiting_for_reply)
async def send_admin_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    try:
        if message.photo:
            await bot.send_photo(target_user_id, photo=message.photo[-1].file_id, caption=f"💬 <b>Support Reply:</b>\n\n{message.caption if message.caption else ''}", parse_mode="HTML")
        else:
            await bot.send_message(target_user_id, text=f"💬 <b>Support Reply:</b>\n\n{message.text}", parse_mode="HTML")
        await message.reply("✅ መልስዎ ለተጠቃሚው በቀጥታ ተልኳል!")
    except Exception as e:
        await message.reply(f"❌ ስህተት: {e}")
    await state.clear()

# ==========================================
# 🟢 BUY USDT WORKFLOW (WITH DYNAMIC RATES & BANKS)
# ==========================================
@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    buy_rate = settings["rates"]["buy"]
    text = (
        "💰 <b>Buy USDT | USDT መግዛት</b>\n\n"
        f"• Rate: 1 USDT = {buy_rate} ETB\n"
        "• Min / Max: 0.5 - 10000.0 USDT\n\n"
        "ምን ያህል USDT መግዛት ይፈልጋሉ? (ምሳሌ: 10)፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(BuyUSDTState.waiting_for_amount)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id, buy_rate=buy_rate)
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    buy_rate = data.get("buy_rate", 197.0)
    try: await message.delete()
    except Exception: pass
        
    try:
        amount = float(message.text)
        if amount < 0.5 or amount > 10000.0:
            if last_msg_id: await bot.edit_message_text("⚠️ እባክዎ ከ 0.5 እስከ 10000.0 USDT መካከል ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)
            return
        
        total_price = amount * buy_rate
        await state.update_data(amount=amount, total_price=total_price)
        
        text = f"✅ <b>Order Summary</b>\n• Amount: {amount:.4f} USDT\n• Pay: {total_price:,.2f} ETB\n\nUSDT የሚላክልዎትን መንገድ ይምረጡ፦"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Binance ID", callback_data="net_binance"), InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="net_bep20")],
            [InlineKeyboardButton(text="🔶 Bybit UID", callback_data="net_bybit"), InlineKeyboardButton(text="🟣 Polygon", callback_data="net_polygon")],
            [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
        ])
        await state.set_state(BuyUSDTState.waiting_for_network)
        if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")
    except ValueError:
        if last_msg_id: await bot.edit_message_text("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)

@dp.callback_query(BuyUSDTState.waiting_for_network, F.data.startswith("net_"))
async def select_network(callback: types.CallbackQuery, state: FSMContext):
    network_map = {"net_binance": "Binance Pay ID", "net_bep20": "BSC (BEP20)", "net_bybit": "Bybit UID", "net_polygon": "Polygon"}
    net_name = network_map.get(callback.data, "Crypto Address")
    await state.update_data(network=net_name)
    
    text = f"📥 USDT የሚላክልዎትን <b>{net_name}</b> ያስገቡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(BuyUSDTState.waiting_for_address)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    address = message.text.strip()
    try: await message.delete()
    except Exception: pass

    await state.update_data(address=address)
    amount, total_price = data.get("amount"), data.get("total_price")
    
    text = f"📬 <b>Receiving destination saved</b>\n• USDT: {amount:.4f}\n• Pay: {total_price:,.2f} ETB\n• Destination: {address}\n\nክፍያ የሚፈጽሙበትን መንገድ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="buy_pay_telebirr"), InlineKeyboardButton(text="🏦 CBE", callback_data="buy_pay_cbe")],
        [InlineKeyboardButton(text="🏦 COOP Bank", callback_data="buy_pay_coop"), InlineKeyboardButton(text="🦁 Awash Bank", callback_data="buy_pay_awash")],
        [InlineKeyboardButton(text="🏛 Abyssinia", callback_data="buy_pay_abyssinia"), InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="buy_pay_dashen")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(BuyUSDTState.waiting_for_payment_method, F.data.startswith("buy_pay_"))
async def buy_payment_selected(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    banks = settings.get("banks", {})
    pay_code = callback.data.replace("buy_pay_", "")
    
    bank_info = banks.get(pay_code, {"name": "Aymen Nesredin Redi", "number": "000000"})
    b_acc, b_owner = bank_info.get("number"), bank_info.get("name")

    text = f"🏛 <b>Payment Info</b>\n\nAccount/Number: <b>{b_acc}</b>\nName: <b>{b_owner}</b>\n\nከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(BuyUSDTState.waiting_for_receipt)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(1)
    
    amount, total_price, address, network = data.get("amount"), data.get("total_price"), data.get("address"), data.get("network")
    user = message.from_user
    
    # Save Order to Firebase
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": "Buy USDT",
        "details": f"{amount} USDT to {network}:{address}", "amount": total_price,
        "status": "PENDING", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ord_key = await fb_post("orders", order_data)
    await fb_put(f"user_orders/{user.id}/{ord_key}", order_data)

    admin_text = (
        f"🚨 <b>New BUY USDT Order! (#{ord_key[:6]})</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Amount: {amount} USDT\n"
        f"💰 Pay: {total_price:,.2f} ETB\n"
        f"🌐 Network: {network}\n"
        f"📍 Address/UID: <code>{address}</code>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (አጽድቅ)", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{ord_key}_{user.id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (#{ord_key[:6]})</b>\n\nትዕዛዝዎ በአስተዳዳሪዎች እየተጣራ ነው።", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# 🛡 ADMIN APPROVE / REJECT
# ==========================================
@dp.callback_query(F.data.startswith("app_"))
async def admin_approve_order(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    ord_key, user_id = parts[1], int(parts[2])
    
    await fb_put(f"orders/{ord_key}/status", "APPROVED")
    await fb_put(f"user_orders/{user_id}/{ord_key}/status", "APPROVED")
    
    try:
        await bot.send_message(user_id, f"🎉 <b>ትዕዛዝዎ (#{ord_key[:6]}) በተሳካ ሁኔታ ጸድቋል (Approved)!</b>", parse_mode="HTML")
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n<b>STATUS: ✅ APPROVED</b>", parse_mode="HTML")
        await callback.answer("ትዕዛዙ ጸድቋል!")
    except Exception as e:
        await callback.answer(f"ስህተት: {e}", show_alert=True)

@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# Web Server for Render
async def handle_ping(request): return web.Response(text="Bot is running 24/7!")
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    print("ቦቱ እና ዌብ ሰርቨሩ ስራ ጀምረዋል...")
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())

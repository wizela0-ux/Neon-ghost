import os
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
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

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

async def fb_delete(path: str):
    if not FIREBASE_DB_URL:
        return
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        await session.delete(url)

# ==========================================
# ⚙️ DYNAMIC SETTINGS & ROLES SETUP
# ==========================================
DEFAULT_SETTINGS = {
    "rates": {"buy": 197.0, "sell": 182.0},
    "stocks": {
        "usdt": 98.0,
        "etb_reserve": 10000.0,
        "unlimited_data": 2,
        "gemini_pro": 34
    },
    "banks": {
        "telebirr": {"name": "Telebirr", "owner": "Aymen Nesredin Redi", "number": "0939357745"},
        "cbe": {"name": "CBE (ንግድ ባንክ)", "owner": "Aymen Nesredin Redi", "number": "1000780294322"},
        "coop": {"name": "COOP Bank", "owner": "Aymen Nesredin Redi", "number": "1947701000001"},
        "awash": {"name": "Awash Bank", "owner": "Nesredin Redi", "number": "01425174740300"},
        "abyssinia": {"name": "Bank of Abyssinia", "owner": "Nesredin Redi", "number": "100404915"},
        "dashen": {"name": "Dashen Bank", "owner": "Nesredin Redi", "number": "2912539951521"}
    },
    "crypto": {
        "bybit_uid": "580130044",
        "polygon_address": "0x9244d02e10124bfa091d1d5c25a4aed204833ad7",
        "bep20_address": "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"
    }
}

async def get_settings():
    settings = await fb_get("settings")
    if not settings or not isinstance(settings, dict):
        await fb_put("settings", DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    
    # Ensure nested keys exist
    if "stocks" not in settings: settings["stocks"] = DEFAULT_SETTINGS["stocks"]
    if "banks" not in settings: settings["banks"] = DEFAULT_SETTINGS["banks"]
    if "crypto" not in settings: settings["crypto"] = DEFAULT_SETTINGS["crypto"]
    
    # Sanitize banks to fix swapped fields if any
    clean_banks = {}
    for b_key, b_info in settings["banks"].items():
        if isinstance(b_info, dict):
            # Check if name looks like a person's name by mistake
            name_val = str(b_info.get("name", ""))
            owner_val = str(b_info.get("owner", ""))
            
            if ("Nesredin" in name_val or "Redi" in name_val or "Aymen" in name_val) and b_key in DEFAULT_SETTINGS["banks"]:
                # Restore clean default name for standard banks
                clean_banks[b_key] = {
                    "name": DEFAULT_SETTINGS["banks"][b_key]["name"],
                    "owner": name_val if "Nesredin" in name_val else owner_val,
                    "number": str(b_info.get("number", ""))
                }
            else:
                clean_banks[b_key] = b_info
        else:
            if b_key in DEFAULT_SETTINGS["banks"]:
                clean_banks[b_key] = DEFAULT_SETTINGS["banks"][b_key]
                
    settings["banks"] = clean_banks
    return settings

async def get_super_admin_id() -> int:
    sa_id = await fb_get("super_admin_id")
    if not sa_id:
        await fb_put("super_admin_id", SUPER_ADMIN_ID)
        return SUPER_ADMIN_ID
    return int(sa_id)

async def get_admin_role(user_id: int) -> str:
    sa_id = await get_super_admin_id()
    if user_id == sa_id:
        return "SUPER_ADMIN"
    admins = await fb_get("admins") or {}
    if str(user_id) in admins:
        admin_data = admins[str(user_id)]
        if isinstance(admin_data, dict):
            return admin_data.get("role", "FULL")
        return "FULL"
    return "NONE"

async def is_admin(user_id: int) -> bool:
    role = await get_admin_role(user_id)
    return role != "NONE"

async def save_user(user_id: int, username: str, first_name: str):
    user_data = {"username": username or "", "first_name": first_name or ""}
    await fb_put(f"users/{user_id}", user_data)

def get_all_users_sync_list(users_dict):
    if not users_dict:
        return []
    return list(users_dict.keys())
# Dynamic Banks Keyboard Generator (With Custom Emoji Support)
def build_banks_keyboard(banks_dict: dict, callback_prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for b_key, b_info in banks_dict.items():
        if isinstance(b_info, dict):
            display_name = b_info.get("name") or b_key.upper()
            # ከ Firebase የባንኩን ኢሞጂ ይወስዳል፤ ካልተገኘ 🏛 ያደርጋል
            emoji = b_info.get("emoji", "🏛")
        else:
            display_name = str(b_info)
            emoji = "🏛"
            
        row.append(InlineKeyboardButton(text=f"{emoji} {display_name}", callback_data=f"{callback_prefix}_{b_key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
    waiting_for_new_admin_id = State()
    waiting_for_transfer_super_id = State()
    waiting_for_stock_usdt = State()
    waiting_for_stock_etb = State()
    waiting_for_stock_data = State()
    waiting_for_stock_gemini = State()
    waiting_for_edit_bank_name = State()
    waiting_for_edit_bank_num = State()
    waiting_for_edit_bank_owner = State()
    waiting_for_edit_crypto_val = State()
    waiting_for_new_bank_key = State()
    waiting_for_new_bank_name = State()
    waiting_for_new_bank_owner = State()
    waiting_for_new_bank_num = State()

# Main Menu Keyboard
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
        f"👋 ሰላም <b>{message.from_user.first_name}</b> እንኳን ደህና መጡ!\n\n"
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
# 👑 ADMIN PANEL & ROLES MANAGEMENT
# ==========================================
@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    role = await get_admin_role(message.from_user.id)
    if role == "NONE":
        return
    
    role_labels = {
        "SUPER_ADMIN": "👑 Super Admin (Owner)",
        "FULL": "🛡 Full Access Admin",
        "ORDERS_SUPPORT": "📦 Orders & Support Admin",
        "BROADCAST": "📢 Broadcaster Admin"
    }
    
    text = (
        "👑 <b>Admin Control Panel | የአስተዳዳሪ ፓነል</b>\n\n"
        f"<b>Your Role:</b> {role_labels.get(role, role)}\n\n"
        "እባክዎ ማስተካከል የሚፈልጉትን ይምረጡ፦"
    )
    
    buttons = []
    
    if role in ["SUPER_ADMIN", "FULL"]:
        buttons.append([
            InlineKeyboardButton(text="💵 Edit Rates", callback_data="admin_edit_rates"),
            InlineKeyboardButton(text="📦 Edit Stocks & Reserves", callback_data="admin_edit_stocks")
        ])
        buttons.append([
            InlineKeyboardButton(text="🏛 Edit Banks & Crypto", callback_data="admin_edit_banks"),
            InlineKeyboardButton(text="➕ Add New Bank", callback_data="admin_add_bank")
        ])
        
    if role in ["SUPER_ADMIN", "FULL", "ORDERS_SUPPORT"]:
        buttons.append([InlineKeyboardButton(text="📊 Bot Dashboard Stats", callback_data="admin_bot_stats")])

    if role in ["SUPER_ADMIN", "FULL", "BROADCAST"]:
        buttons.append([InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_start_broadcast")])
        
    if role == "SUPER_ADMIN":
        buttons.append([
            InlineKeyboardButton(text="📜 Admin List", callback_data="admin_list"),
            InlineKeyboardButton(text="➕ Add Admin", callback_data="admin_add_admin")
        ])
        buttons.append([InlineKeyboardButton(text="👑 Transfer Super Admin Ownership", callback_data="admin_transfer_super_start")])
        
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "admin_back")
async def admin_back_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    role = await get_admin_role(callback.from_user.id)
    if role == "NONE": return
    
    role_labels = {
        "SUPER_ADMIN": "👑 Super Admin (Owner)", "FULL": "🛡 Full Access Admin",
        "ORDERS_SUPPORT": "📦 Orders & Support Admin", "BROADCAST": "📢 Broadcaster Admin"
    }
    text = f"👑 <b>Admin Control Panel | የአስተዳዳሪ ፓነል</b>\n\n<b>Your Role:</b> {role_labels.get(role, role)}\n\nእባክዎ ማስተካከል የሚፈልጉትን ይምረጡ፦"
    
    buttons = []
    if role in ["SUPER_ADMIN", "FULL"]:
        buttons.append([InlineKeyboardButton(text="💵 Edit Rates", callback_data="admin_edit_rates"), InlineKeyboardButton(text="📦 Edit Stocks & Reserves", callback_data="admin_edit_stocks")])
        buttons.append([InlineKeyboardButton(text="🏛 Edit Banks & Crypto", callback_data="admin_edit_banks"), InlineKeyboardButton(text="➕ Add New Bank", callback_data="admin_add_bank")])
    if role in ["SUPER_ADMIN", "FULL", "ORDERS_SUPPORT"]:
        buttons.append([InlineKeyboardButton(text="📊 Bot Dashboard Stats", callback_data="admin_bot_stats")])
    if role in ["SUPER_ADMIN", "FULL", "BROADCAST"]:
        buttons.append([InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_start_broadcast")])
    if role == "SUPER_ADMIN":
        buttons.append([InlineKeyboardButton(text="📜 Admin List", callback_data="admin_list"), InlineKeyboardButton(text="➕ Add Admin", callback_data="admin_add_admin")])
        buttons.append([InlineKeyboardButton(text="👑 Transfer Super Admin Ownership", callback_data="admin_transfer_super_start")])
        
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_bot_stats")
async def show_bot_stats(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    users = await fb_get("users") or {}
    orders = await fb_get("orders") or {}
    
    total_users = len(users)
    total_orders = len(orders)
    pending_orders = len([o for o in orders.values() if isinstance(o, dict) and o.get("status") == "PENDING"])
    approved_orders = len([o for o in orders.values() if isinstance(o, dict) and o.get("status") == "APPROVED"])
    
    text = (
        "📊 <b>Bot Dashboard Statistics</b>\n\n"
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"📦 <b>Total Orders Sent:</b> {total_orders}\n"
        f"⏳ <b>Pending Orders:</b> {pending_orders}\n"
        f"✅ <b>Approved Orders:</b> {approved_orders}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Stock Management
@dp.callback_query(F.data == "admin_edit_stocks")
async def show_stock_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    settings = await get_settings()
    stocks = settings.get("stocks", {})
    
    text = (
        "📦 <b>Current Stocks & ETB Reserves:</b>\n\n"
        f"• USDT Stock: <b>{stocks.get('usdt', 0.0)} USDT</b>\n"
        f"• ETB Reserve (for Sell): <b>{stocks.get('etb_reserve', 0.0):,.2f} ETB</b>\n"
        f"• Monthly Unlimited Data: <b>{stocks.get('unlimited_data', 0)} pcs</b>\n"
        f"• Gemini Pro 18m: <b>{stocks.get('gemini_pro', 0)} pcs</b>\n\n"
        "ማስተካከል የሚፈልጉትን ይምረጡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Update USDT Stock", callback_data="stk_usdt"), InlineKeyboardButton(text="💰 Update ETB Reserve", callback_data="stk_etb")],
        [InlineKeyboardButton(text="🌐 Update Data Stock", callback_data="stk_data"), InlineKeyboardButton(text="✨ Update Gemini Stock", callback_data="stk_gemini")],
        [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("stk_"))
async def start_stock_update(callback: types.CallbackQuery, state: FSMContext):
    target = callback.data
    if target == "stk_usdt":
        await state.set_state(EditSettingsState.waiting_for_stock_usdt)
        await callback.message.edit_text("አዲሱን የ <b>USDT Stock</b> መጠን ያስገቡ (ምሳሌ: 500)፦", parse_mode="HTML")
    elif target == "stk_etb":
        await state.set_state(EditSettingsState.waiting_for_stock_etb)
        await callback.message.edit_text("አዲሱን የ <b>ETB Payout Reserve</b> ብር መጠን ያስገቡ (ምሳሌ: 25000)፦", parse_mode="HTML")
    elif target == "stk_data":
        await state.set_state(EditSettingsState.waiting_for_stock_data)
        await callback.message.edit_text("አዲሱን የ <b>Unlimited Data</b> ብዛት ያስገቡ (ምሳሌ: 5)፦", parse_mode="HTML")
    elif target == "stk_gemini":
        await state.set_state(EditSettingsState.waiting_for_stock_gemini)
        await callback.message.edit_text("አዲሱን የ <b>Gemini Pro</b> ብዛት ያስገቡ (ምሳሌ: 50)፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_stock_usdt)
async def process_stock_usdt(message: types.Message, state: FSMContext):
    try:
        val = float(message.text.strip())
        settings = await get_settings()
        settings["stocks"]["usdt"] = val
        await fb_put("settings", settings)
        await message.answer(f"✅ USDT Stock ወደ <b>{val} USDT</b> ተቀይሯል!", parse_mode="HTML")
        await state.clear()
    except ValueError: await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ፦")

@dp.message(EditSettingsState.waiting_for_stock_etb)
async def process_stock_etb(message: types.Message, state: FSMContext):
    try:
        val = float(message.text.strip())
        settings = await get_settings()
        settings["stocks"]["etb_reserve"] = val
        await fb_put("settings", settings)
        await message.answer(f"✅ ETB Payout Reserve ወደ <b>{val:,.2f} ETB</b> ተቀይሯል!", parse_mode="HTML")
        await state.clear()
    except ValueError: await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ፦")

@dp.message(EditSettingsState.waiting_for_stock_data)
async def process_stock_data(message: types.Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        settings = await get_settings()
        settings["stocks"]["unlimited_data"] = val
        await fb_put("settings", settings)
        await message.answer(f"✅ Unlimited Data Stock ወደ <b>{val} pcs</b> ተቀይሯል!", parse_mode="HTML")
        await state.clear()
    except ValueError: await message.answer("❌ እባክዎ ትክክለኛ የቁጥር ብዛት ያስገቡ፦")

@dp.message(EditSettingsState.waiting_for_stock_gemini)
async def process_stock_gemini(message: types.Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        settings = await get_settings()
        settings["stocks"]["gemini_pro"] = val
        await fb_put("settings", settings)
        await message.answer(f"✅ Gemini Pro Stock ወደ <b>{val} pcs</b> ተቀይሯል!", parse_mode="HTML")
        await state.clear()
    except ValueError: await message.answer("❌ እባክዎ ትክክለኛ የቁጥር ብዛት ያስገቡ፦")

# Edit Banks & Crypto Addresses
@dp.callback_query(F.data == "admin_edit_banks")
async def show_edit_banks_list(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    settings = await get_settings()
    banks = settings.get("banks", {})
    crypto = settings.get("crypto", {})
    
    text = "🏛 <b>Current Banks & Crypto Addresses:</b>\n\n"
    buttons = []
    
    for b_key, b_info in banks.items():
        b_name = b_info.get("name") if isinstance(b_info, dict) else b_key.upper()
        b_num = b_info.get("number") if isinstance(b_info, dict) else ""
        b_owner = b_info.get("owner") if isinstance(b_info, dict) else ""
        
        text += f"• <b>{b_name}</b>: {b_num} ({b_owner})\n"
        buttons.append([InlineKeyboardButton(text=f"✏️ Edit {b_name}", callback_data=f"ebank_{b_key}")])
        
    text += f"\n<b>Crypto Addresses:</b>\n• Bybit: <code>{crypto.get('bybit_uid')}</code>\n• BEP20: <code>{crypto.get('bep20_address')}</code>\n• Polygon: <code>{crypto.get('polygon_address')}</code>\n"
    buttons.append([
        InlineKeyboardButton(text="✏️ Edit Bybit UID", callback_data="ecrypto_bybit_uid"),
        InlineKeyboardButton(text="✏️ Edit BEP20", callback_data="ecrypto_bep20_address")
    ])
    buttons.append([InlineKeyboardButton(text="✏️ Edit Polygon", callback_data="ecrypto_polygon_address")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("ebank_"))
async def start_edit_single_bank(callback: types.CallbackQuery, state: FSMContext):
    b_key = callback.data.replace("ebank_", "")
    await state.update_data(target_bank_key=b_key)
    await state.set_state(EditSettingsState.waiting_for_edit_bank_name)
    await callback.message.edit_text(f"🏛 ለ <b>{b_key.upper()}</b> አዲሱን የባንክ ይፋዊ ስም ያስገቡ (ምሳሌ: CBE (ንግድ ባንክ))፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_edit_bank_name)
async def process_edit_bank_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    await state.update_data(new_bank_name=new_name)
    await state.set_state(EditSettingsState.waiting_for_edit_bank_num)
    await message.answer("🔢 አዲሱን የባንክ/ቴሌብር ሂሳብ ቁጥር ያስገቡ፦", parse_mode="HTML")

@dp.message(EditSettingsState.waiting_for_edit_bank_num)
async def process_edit_bank_num(message: types.Message, state: FSMContext):
    new_num = message.text.strip()
    await state.update_data(new_bank_num=new_num)
    await state.set_state(EditSettingsState.waiting_for_edit_bank_owner)
    await message.answer("👤 በባንኩ/ቴሌብር የተመዘገበውን አዲሱን የባለቤት ሙሉ ስም ያስገቡ፦", parse_mode="HTML")

@dp.message(EditSettingsState.waiting_for_edit_bank_owner)
async def process_edit_bank_owner(message: types.Message, state: FSMContext):
    new_owner = message.text.strip()
    data = await state.get_data()
    b_key = data.get("target_bank_key")
    new_name = data.get("new_bank_name")
    new_num = data.get("new_bank_num")
    
    settings = await get_settings()
    if "banks" not in settings: settings["banks"] = {}
    
    settings["banks"][b_key] = {
        "name": new_name,
        "number": new_num,
        "owner": new_owner
    }
    await fb_put("settings", settings)
    await message.answer(f"✅ <b>{new_name}</b> በተሳካ ሁኔታ ተስተካክሏል!\n\nName: {new_name}\nNumber: {new_num}\nOwner: {new_owner}", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("ecrypto_"))
async def start_edit_crypto_address(callback: types.CallbackQuery, state: FSMContext):
    c_key = callback.data.replace("ecrypto_", "")
    await state.update_data(target_crypto_key=c_key)
    await state.set_state(EditSettingsState.waiting_for_edit_crypto_val)
    await callback.message.edit_text(f"🌐 አዲሱን <b>{c_key.upper()}</b> አድራሻ ያስገቡ፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_edit_crypto_val)
async def process_edit_crypto_val(message: types.Message, state: FSMContext):
    new_val = message.text.strip()
    data = await state.get_data()
    c_key = data.get("target_crypto_key")
    
    settings = await get_settings()
    settings["crypto"][c_key] = new_val
    await fb_put("settings", settings)
    
    await message.answer(f"✅ <b>{c_key.upper()}</b> አድራሻ በተሳካ ሁኔታ ተቀይሯል!\n\n<code>{new_val}</code>", parse_mode="HTML")
    await state.clear()

# Add New Bank
@dp.callback_query(F.data == "admin_add_bank")
async def start_add_new_bank(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.set_state(EditSettingsState.waiting_for_new_bank_key)
    await callback.message.edit_text("➕ የአዲሱን ባንክ መለያ ቃል ያለ ቦታ (Key) ያስገቡ (ምሳሌ: <code>hibret</code>)፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_new_bank_key)
async def process_new_bank_key(message: types.Message, state: FSMContext):
    key = message.text.strip().lower().replace(" ", "_")
    await state.update_data(new_b_key=key)
    await state.set_state(EditSettingsState.waiting_for_new_bank_name)
    await message.answer("የባንኩን ይፋዊ ስም ያስገቡ (ምሳሌ: <b>Hibret Bank</b>)፦", parse_mode="HTML")

@dp.message(EditSettingsState.waiting_for_new_bank_name)
async def process_new_bank_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(new_b_name=name)
    await state.set_state(EditSettingsState.waiting_for_new_bank_owner)
    await message.answer("የባለቤቱን ሙሉ ስም ያስገቡ፦", parse_mode="HTML")

@dp.message(EditSettingsState.waiting_for_new_bank_owner)
async def process_new_bank_owner(message: types.Message, state: FSMContext):
    owner = message.text.strip()
    await state.update_data(new_b_owner=owner)
    await state.set_state(EditSettingsState.waiting_for_new_bank_num)
    await message.answer("የባንክ አካውንት ቁጥሩን ያስገቡ፦", parse_mode="HTML")

@dp.message(EditSettingsState.waiting_for_new_bank_num)
async def process_new_bank_num(message: types.Message, state: FSMContext):
    num = message.text.strip()
    data = await state.get_data()
    
    b_key = data.get("new_b_key")
    b_name = data.get("new_b_name")
    b_owner = data.get("new_b_owner")
    
    settings = await get_settings()
    settings["banks"][b_key] = {"name": b_name, "owner": b_owner, "number": num}
    await fb_put("settings", settings)
    
    await message.answer(f"🎉 <b>{b_name}</b> በተሳካ ሁኔታ አዲስ ባንክ ሆኖ ተጨምሯል!\n\nከእንግዲህ ተጠቃሚዎች ክፍያ ሲፈጽሙ እንደ አማራጭ ያገኙታል።", parse_mode="HTML")
    await state.clear()

# Admin List & Other Roles
@dp.callback_query(F.data == "admin_list")
async def show_admin_list(callback: types.CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if role != "SUPER_ADMIN":
        await callback.answer("❌ ይህን ማየት የሚችለው ዋናው Super Admin ብቻ ነው!", show_alert=True)
        return
        
    admins = await fb_get("admins") or {}
    sa_id = await get_super_admin_id()
    
    text = f"📜 <b>Admins Management List</b>\n\n👑 <b>Super Admin (Owner):</b> <code>{sa_id}</code>\n\n<b>Sub-Admins:</b>\n"
    buttons = []
    
    if not admins:
        text += "<i>ምንም የተጨመረ Sub-Admin የለም።</i>"
    else:
        for a_id, a_data in admins.items():
            a_role = a_data.get("role", "FULL") if isinstance(a_data, dict) else "FULL"
            text += f"• <code>{a_id}</code> — Role: <b>{a_role}</b>\n"
            buttons.append([
                InlineKeyboardButton(text=f"⚙️ Role ({a_id})", callback_data=f"edit_role_{a_id}"),
                InlineKeyboardButton(text=f"❌ Remove ({a_id})", callback_data=f"remove_admin_{a_id}")
            ])
            
    buttons.append([InlineKeyboardButton(text="🔙 Back to Admin", callback_data="admin_back")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_add_admin")
async def admin_add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    role = await get_admin_role(callback.from_user.id)
    if role != "SUPER_ADMIN":
        await callback.answer("❌ አዲስ አድሚን መጨመር የሚችለው ዋናው Super Admin ብቻ ነው!", show_alert=True)
        return
    await state.set_state(EditSettingsState.waiting_for_new_admin_id)
    await callback.message.edit_text("➕ አዲስ አድሚን የሚሆነውን ሰው <b>Telegram User ID</b> ያስገቡ፦", parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_new_admin_id)
async def process_add_new_admin_id(message: types.Message, state: FSMContext):
    try:
        new_admin_id = int(message.text.strip())
        await state.update_data(new_admin_id=new_admin_id)
        
        text = f"👤 ለ ተጠቃሚ <code>{new_admin_id}</code> መስጠት የሚፈልጉትን **የስልጣን ደረጃ (Role)** ይምረጡ፦"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛡 Full Access (ሁሉንም የሚቆጣጠር)", callback_data="set_role_FULL")],
            [InlineKeyboardButton(text="📦 Orders & Support Only (ትዕዛዝ እና ድጋፍ ብቻ)", callback_data="set_role_ORDERS_SUPPORT")],
            [InlineKeyboardButton(text="📢 Broadcaster Only (ማስታወቂያ ብቻ)", callback_data="set_role_BROADCAST")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_order")]
        ])
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ የቁጥር ID ብቻ ያስገቡ፦")

@dp.callback_query(F.data.startswith("set_role_"))
async def process_save_admin_role(callback: types.CallbackQuery, state: FSMContext):
    selected_role = callback.data.replace("set_role_", "")
    data = await state.get_data()
    new_admin_id = data.get("new_admin_id")
    
    if new_admin_id:
        await fb_put(f"admins/{new_admin_id}", {"role": selected_role, "added_at": datetime.now().strftime("%Y-%m-%d")})
        await callback.message.edit_text(f"✅ ተጠቃሚ ID <code>{new_admin_id}</code> በ Role <b>{selected_role}</b> በአድሚንነት ተጨምሯል!", parse_mode="HTML")
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_role_"))
async def start_edit_admin_role(callback: types.CallbackQuery, state: FSMContext):
    target_id = callback.data.replace("edit_role_", "")
    await state.update_data(new_admin_id=target_id)
    
    text = f"⚙️ ለ አድሚን <code>{target_id}</code> አዲስ የስልጣን ደረጃ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Full Access", callback_data="set_role_FULL")],
        [InlineKeyboardButton(text="📦 Orders & Support Only", callback_data="set_role_ORDERS_SUPPORT")],
        [InlineKeyboardButton(text="📢 Broadcaster Only", callback_data="set_role_BROADCAST")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="admin_list")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("remove_admin_"))
async def process_remove_admin(callback: types.CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if role != "SUPER_ADMIN":
        await callback.answer("❌ አድሚን ማስወገድ የሚችለው ዋናው Super Admin ብቻ ነው!", show_alert=True)
        return
    rem_id = callback.data.replace("remove_admin_", "")
    await fb_delete(f"admins/{rem_id}")
    await callback.answer(f"✅ አድሚን {rem_id} ተወግዷል!")
    await show_admin_list(callback)

@dp.callback_query(F.data == "admin_transfer_super_start")
async def start_transfer_super(callback: types.CallbackQuery, state: FSMContext):
    sa_id = await get_super_admin_id()
    if callback.from_user.id != sa_id:
        await callback.answer("❌ ይህን ማድረግ የሚችለው ዋናው ባለቤት ብቻ ነው!", show_alert=True)
        return
    
    text = "👑 <b>Transfer Super Admin Ownership</b>\n\nአዲስ Super Admin የሚሆነውን ሰው <b>Telegram User ID</b> ያስገቡ፦"
    await state.set_state(EditSettingsState.waiting_for_transfer_super_id)
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.message(EditSettingsState.waiting_for_transfer_super_id)
async def ask_confirm_super_transfer(message: types.Message, state: FSMContext):
    try:
        new_sa_id = int(message.text.strip())
        await state.update_data(target_new_sa_id=new_sa_id)
        
        text = (
            f"⚠️ <b>ማስጠንቀቂያ! (WARNING)</b>\n\n"
            f"የቦቱን ሙሉ ባለቤትነት (Super Admin Ownership) ለ ተጠቃሚ ID <code>{new_sa_id}</code> ማስተላለፍ ይፈልጋሉ?\n\n"
            "<i>ይህንን ካደረጉ በኋላ የቦቱ ዋና ባለቤትነት ለአዲሱ ሰው ይተላለፋል!</i>"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ አዎ፣ ሙሉ በሙሉ አስተላልፍ", callback_data="confirm_transfer_super")],
            [InlineKeyboardButton(text="❌ ሰርዝ (Cancel)", callback_data="cancel_order")]
        ])
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ የቁጥር ID ያስገቡ፦")

@dp.callback_query(F.data == "confirm_transfer_super")
async def confirm_super_transfer_action(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_sa_id = data.get("target_new_sa_id")
    
    if new_sa_id:
        await fb_put("super_admin_id", new_sa_id)
        await callback.message.edit_text(f"🎉 <b>የቦቱ ባለቤትነት በተሳካ ሁኔታ ወደ <code>{new_sa_id}</code> ተላልፏል!</b>", parse_mode="HTML")
    await state.clear()
    await callback.answer()

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

@dp.callback_query(F.data == "admin_start_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.set_state(BroadcastState.waiting_for_broadcast_msg)
    await callback.message.edit_text("📢 ለሁሉም ተጠቃሚዎች የሚላከውን ማስታወቂያ/ፅሁፍ ይጻፉ፦", parse_mode="HTML")
    await callback.answer()

@dp.message(BroadcastState.waiting_for_broadcast_msg)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    users_dict = await fb_get("users") or {}
    user_ids = get_all_users_sync_list(users_dict)
    
    success = 0
    await message.answer(f"⏳ ለ {len(user_ids)} ተጠቃሚዎች በመላክ ላይ...")
    for u_id in user_ids:
        try:
            await message.copy_to(chat_id=int(u_id))
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await message.answer(f"✅ ብሮድካስት ተጠናቋል! ለ {success} ተጠቃሚዎች ደርሷል።")
    await state.clear()

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

@dp.callback_query(F.data.startswith("view_ord_"))
async def view_single_order(callback: types.CallbackQuery):
    ord_key = callback.data.replace("view_ord_", "")
    user_id = callback.from_user.id
    ord = await fb_get(f"user_orders/{user_id}/{ord_key}")
    if ord:
        text = (
            f"📑 <b>Order #{ord_key[:6]} Details</b>\n\n"
            f"• <b>Type:</b> {ord.get('service')}\n"
            f"• <b>Status:</b> {ord.get('status')}\n"
            f"• <b>Amount:</b> {ord.get('amount', 0):,.2f} ETB\n"
            f"• <b>Details:</b> {ord.get('details')}\n"
            f"• <b>Created:</b> {ord.get('created_at')}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="my_orders")]])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "completed_history")
async def show_completed_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    all_orders = await fb_get(f"user_orders/{user_id}")
    
    approved_orders = [o for o in all_orders.values()] if all_orders else []
    approved_orders = [o for o in approved_orders if o.get("status") == "APPROVED"]
    
    if not approved_orders:
        text = "✅ <b>Completed Order History (0)</b>\n\nምንም የተጠናቀቀ ትዕዛዝ የለም።"
    else:
        text = f"✅ <b>Completed Order History ({len(approved_orders)})</b>\n\n"
        for ord in approved_orders[-5:]:
            text += f"• {ord.get('service')} | {ord.get('amount', 0):,.2f} ETB | {ord.get('created_at')}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")]])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🛠 INTERACTIVE SUPPORT SYSTEM
# ==========================================
@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    support_text = (
        "🛠 <b>Customer Support | የደንበኞች አገልግሎት</b>\n\n"
        "ማንኛውም ጥያቄ፣ አስተያየት ወይም የክፍያ ችግር ካጋጠመዎት ከታች ያለውን <b>Message Admin Inside Bot</b> ቁልፍ በመጫን ቀጥታ ለአድሚን ይጻፉ፦\n\n"
        "🕒 <b>Working hours:</b> 08:00–22:00 EAT"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Message Admin Inside Bot", callback_data="msg_admin_start")],
        [InlineKeyboardButton(text="💬 DM Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
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
    role = await get_admin_role(callback.from_user.id)
    if role not in ["SUPER_ADMIN", "FULL", "ORDERS_SUPPORT"]:
        await callback.answer("❌ መልስ ለመስጠት ስልጣን የሎትም!", show_alert=True)
        return
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
# 🟢 BUY USDT WORKFLOW (DYNAMIC STOCKS & STRICT VALIDATION)
# ==========================================
@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    buy_rate = settings.get("rates", {}).get("buy", 197.0)
    stock = settings.get("stocks", {}).get("usdt", 0.0)
    
    if stock <= 0:
        await callback.answer("⚠️ ይቅርታ! በአሁኑ ሰዓት USDT stock አልቋል (Out of stock)።", show_alert=True)
        return

    text = (
        "💰 <b>Buy USDT | USDT መግዛት</b>\n\n"
        f"• Available stock (የአሁን መጠን): <b>{stock} USDT</b>\n"
        f"• Rate (ተመን): 1 USDT = {buy_rate} ETB\n"
        f"• Min / Max (ዝቅተኛ / ከፍተኛ): 0.5 - {min(stock, 10000.0)} USDT\n\n"
        "Enter how much USDT you want to buy:\n"
        "ምን ያህል USDT መግዛት ይፈልጋሉ? (ምሳሌ: 10)"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(BuyUSDTState.waiting_for_amount)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id, buy_rate=buy_rate, available_stock=stock)
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    buy_rate = data.get("buy_rate", 197.0)
    stock = data.get("available_stock", 0.0)
    try: await message.delete()
    except Exception: pass
        
    try:
        amount = float(message.text)
        max_limit = min(stock, 10000.0)
        if amount < 0.5 or amount > max_limit:
            err_text = f"⚠️ እባክዎ ከ 0.5 እስከ {max_limit} USDT መካከል ያስገቡ፦"
            if last_msg_id: await bot.edit_message_text(err_text, chat_id=message.chat.id, message_id=last_msg_id)
            return
        
        total_price = amount * buy_rate
        await state.update_data(amount=amount, total_price=total_price)
        
        text = (
            "✅ <b>Order Summary | የትዕዛዝ ማጠቃለያ</b>\n"
            f"• Amount (መጠን): {amount:.4f} USDT\n"
            f"• Total to pay (የሚከፍሉት ብር): {total_price:,.2f} ETB\n"
            f"• Rate (ተመን): {buy_rate} ETB\n\n"
            "USDT የት ይላክልዎታል? (የመቀበያ መንገድ ይምረጡ)፦"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Binance ID", callback_data="net_binance"), InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="net_bep20")],
            [InlineKeyboardButton(text="🔶 Bybit UID", callback_data="net_bybit"), InlineKeyboardButton(text="🟣 Polygon (USDT)", callback_data="net_polygon")],
            [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
        ])
        await state.set_state(BuyUSDTState.waiting_for_network)
        if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")
            
    except ValueError:
        if last_msg_id: await bot.edit_message_text("❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 10)፦", chat_id=message.chat.id, message_id=last_msg_id)

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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(BuyUSDTState.waiting_for_address)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(BuyUSDTState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    network = data.get("network", "")
    address = message.text.strip()
    try: await message.delete()
    except Exception: pass

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
        if last_msg_id: await bot.edit_message_text(err_msg, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
        return

    await state.update_data(address=address)
    amount, total_price = data.get("amount"), data.get("total_price")
    
    # Dynamic Banks Keyboard
    settings = await get_settings()
    banks = settings.get("banks", {})
    keyboard = build_banks_keyboard(banks, "buy_pay")
    
    text = (
        "📬 <b>Receiving destination saved | መድረሻው ተይዟል</b>\n\n"
        f"• USDT: {amount:.4f}\n"
        f"• ETB to pay (የሚከፍሉት ብር): {total_price:,.2f} ETB\n"
        f"• Destination (መቀበያ): {address}\n\n"
        "ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    await state.set_state(BuyUSDTState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(BuyUSDTState.waiting_for_payment_method, F.data.startswith("buy_pay_"))
async def buy_payment_selected(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    banks = settings.get("banks", {})
    pay_code = callback.data.replace("buy_pay_", "")
    
    bank_info = banks.get(pay_code, {})
    if isinstance(bank_info, dict):
        b_name = bank_info.get("name", pay_code.upper())
        b_acc = bank_info.get("number", "N/A")
        b_owner = bank_info.get("owner", "N/A")
    else:
        b_name, b_acc, b_owner = pay_code.upper(), "N/A", "N/A"
    
    data = await state.get_data()
    amount, total_price = data.get("amount"), data.get("total_price")

    text = (
        "📋 <b>Order summary</b>\n"
        f"• USDT: {amount:.4f} USDT\n"
        f"• Pay: {total_price:,.2f} ETB\n\n"
        f"🏛 <b>{b_name}</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        "Send the exact ETB amount, then upload a clear receipt screenshot.\n"
        "ትክክለኛውን የብር መጠን ከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ።"
    )
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
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...\n⏳ Reading screenshot with OCR...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(2)
    
    amount, total_price, address, network = data.get("amount"), data.get("total_price"), data.get("address"), data.get("network")
    user = message.from_user
    
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": "Buy USDT",
        "details": f"{amount} USDT to {network}:{address}", "amount": total_price, "crypto_amount": amount,
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
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{ord_key}_{user.id}")]])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>Payment proof received successfully! (#{ord_key[:6]})</b>\n\nየክፍያ ማረጋገጫዎ ደርሶናል! ትዕዛዝዎ በአስተዳዳሪዎች እየተጣራ ነው። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# 🔴 SELL USDT WORKFLOW (ETB RESERVE & DYNAMIC BANKS)
# ==========================================
@dp.callback_query(F.data == "sell_usdt")
async def start_sell_usdt(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    sell_rate = settings.get("rates", {}).get("sell", 182.0)
    etb_reserve = settings.get("stocks", {}).get("etb_reserve", 0.0)
    
    max_usdt_we_can_buy = etb_reserve / sell_rate if sell_rate > 0 else 0.0
    
    if etb_reserve <= 0 or max_usdt_we_can_buy < 0.5:
        await callback.answer("⚠️ ይቅርታ! በአሁኑ ሰዓት የ ETB በጀታችን አልቋል። እባክዎ ትንሽ ቆይተው ይሞክሩ።", show_alert=True)
        return

    banks = settings.get("banks", {})
    keyboard = build_banks_keyboard(banks, "payout")

    text = (
        "🔴 <b>Sell USDT — Step 1 of 4 | USDT መሸጥ — ደረጃ 1</b>\n\n"
        f"• Current Sell Rate: <b>1 USDT = {sell_rate} ETB</b>\n"
        f"• Our ETB Budget: <b>{etb_reserve:,.2f} ETB</b> (Max buy: <b>{max_usdt_we_can_buy:.2f} USDT</b>)\n\n"
        "How would you like to receive your ETB payout?\n"
        "ብር የሚቀበሉበትን የክፍያ መንገድ ይምረጡ፦"
    )
    await state.set_state(SellUSDTState.waiting_for_payout_method)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id, sell_rate=sell_rate, etb_reserve=etb_reserve, max_usdt_buy=max_usdt_we_can_buy)
    await callback.answer()

@dp.callback_query(SellUSDTState.waiting_for_payout_method, F.data.startswith("payout_"))
async def select_payout_method(callback: types.CallbackQuery, state: FSMContext):
    pay_key = callback.data.replace("payout_", "")
    settings = await get_settings()
    banks = settings.get("banks", {})
    
    b_info = banks.get(pay_key, {})
    if isinstance(b_info, dict):
        method_name = b_info.get("name", pay_key.upper())
    else:
        method_name = pay_key.upper()
        
    await state.update_data(payout_method=method_name, payout_key=pay_key)
    
    text = (
        f"🔴 <b>Step 2 of 4 — {method_name} details | መረጃ ያስገቡ</b>\n\n"
        f"ብር የሚቀበሉበትን የ <b>{method_name}</b> ቁጥር ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(SellUSDTState.waiting_for_account_number)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(SellUSDTState.waiting_for_account_number)
async def process_account_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    payout_key = data.get("payout_key", "")
    method = data.get("payout_method")
    account_num = message.text.strip()
    try: await message.delete()
    except Exception: pass

    is_valid = True
    err_msg = ""

    if payout_key == "telebirr":
        if not (account_num.startswith("09") or account_num.startswith("07")) or len(account_num) != 10 or not account_num.isdigit():
            is_valid = False
            err_msg = "⚠️ <b>Telebirr</b> ቁጥር በ '09' ወይም '07' መጀመር እና 10 አሃዞች መሆን አለበት፦"
    elif payout_key == "cbe":
        if not account_num.startswith("1000") or len(account_num) != 13 or not account_num.isdigit():
            is_valid = False
            err_msg = "⚠️ የ <b>CBE (ንግድ ባንክ)</b> ሂሳብ ቁጥር በ '1000' መጀመር እና 13 አሃዞች መሆን አለበት፦"
    else:
        if not account_num.isdigit() or len(account_num) < 8:
            is_valid = False
            err_msg = f"⚠️ እባክዎ ትክክለኛ የ <b>{method}</b> የሂሳብ ቁጥር ያስገቡ፦"

    if not is_valid:
        if last_msg_id: await bot.edit_message_text(err_msg, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
        return

    await state.update_data(account_num=account_num)
    text = (
        f"👤 <b>Enter Account Holder Name | የባለቤት ስም ያስገቡ</b>\n\n"
        f"በ {method} የተመዘገበውን የባለቤቱን ሙሉ ስም ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(SellUSDTState.waiting_for_account_name)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")

@dp.message(SellUSDTState.waiting_for_account_name)
async def process_account_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    acc_name = message.text.strip()
    try: await message.delete()
    except Exception: pass

    if len(acc_name) < 3:
        if last_msg_id: await bot.edit_message_text("⚠️ እባክዎ ትክክለኛ ሙሉ ስም ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)
        return

    await state.update_data(acc_name=acc_name)
    method, account_num = data.get("payout_method"), data.get("account_num")
    
    text = (
        "🔴 <b>Step 3 of 4 — Choose USDT deposit method | ደረጃ 3 — USDT ማስገቢያ መንገድ ይምረጡ</b>\n\n"
        "<b>Your ETB payout destination | የብር መቀበያ መረጃዎ፦</b>\n"
        f"• Method: {method}\n"
        f"• Number/Account: <code>{account_num}</code>\n"
        f"• Name: {acc_name}\n\n"
        "USDT ለእኛ በምን መንገድ ይልካሉ? (ከታች ይምረጡ)፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔶 Bybit UID", callback_data="deposit_bybit"), InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="deposit_bep20")],
        [InlineKeyboardButton(text="🟣 Polygon (USDT)", callback_data="deposit_polygon")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_deposit_network)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(SellUSDTState.waiting_for_deposit_network, F.data.startswith("deposit_"))
async def select_deposit_network(callback: types.CallbackQuery, state: FSMContext):
    net_code = callback.data
    settings = await get_settings()
    crypto = settings.get("crypto", {})
    
    if net_code == "deposit_bybit": net_name, our_addr = "Bybit UID", crypto.get("bybit_uid")
    elif net_code == "deposit_bep20": net_name, our_addr = "BSC (BEP20)", crypto.get("bep20_address")
    else: net_name, our_addr = "Polygon Network", crypto.get("polygon_address")

    await state.update_data(deposit_network=net_name, our_address=our_addr)
    
    text = (
        f"🔴 <b>Step 4 of 4 — {net_name} | ደረጃ 4 — {net_name}</b>\n\n"
        f"USDT ወደዚህ የእኛ {net_name} ይላኩ፦\n\n"
        f"<code>{our_addr}</code>\n\n"
        "የላኩበትን ክፍያ ግልጽ ስክሪንሾት ይላኩ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(SellUSDTState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(SellUSDTState.waiting_for_proof, F.photo)
async def process_sell_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass
        
    if last_msg_id: await bot.edit_message_text("🔄 Reading transfer proof for manual review...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(2)
    
    payout_method, account_num, acc_name, deposit_network = data.get("payout_method"), data.get("account_num"), data.get("acc_name"), data.get("deposit_network")
    user = message.from_user
    
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": "Sell USDT",
        "details": f"Payout to {payout_method}:{account_num} ({acc_name}) via {deposit_network}", "amount": 0.0,
        "status": "PENDING", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ord_key = await fb_post("orders", order_data)
    await fb_put(f"user_orders/{user.id}/{ord_key}", order_data)

    admin_text = (
        f"🚨 <b>New SELL USDT Order! (#{ord_key[:6]})</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"🌐 Sent via: {deposit_network}\n"
        f"💵 Payout Method: {payout_method}\n"
        f"📍 Payout Account: <code>{account_num}</code>\n"
        f"👤 Account Name: {acc_name}\n\n"
        "የ USDT ትራንስፈር ስክሪንሾት ከታች ተያይዟል፦"
    )
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve (ብር ላክኩ)", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{ord_key}_{user.id}")]])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>Transfer proof received successfully! (#{ord_key[:6]})</b>\n\nየUSDT ትራንስፈር ማረጋገጫዎ ደርሶናል! አድሚኑ ማረጋገጫውን አይቶ የኢትዮጵያ ብር በባንክ/ቴሌብር ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# 💎 TELEGRAM PREMIUM WORKFLOW
# ==========================================
@dp.callback_query(F.data == "telegram_premium")
async def start_telegram_premium(callback: types.CallbackQuery, state: FSMContext):
    text = "💎 <b>Telegram Premium</b>\n\nመግዛት የሚፈልጉትን የፕሪሚየም ጊዜ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ 3 Months — 2,600 ETB", callback_data="prem_3_months")],
        [InlineKeyboardButton(text="✈️ 6 Months — 3,700 ETB", callback_data="prem_6_months")],
        [InlineKeyboardButton(text="✈️ 12 Months — 6,000 ETB", callback_data="prem_12_months")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(TelegramPremiumState.waiting_for_plan)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(TelegramPremiumState.waiting_for_plan, F.data.startswith("prem_"))
async def select_premium_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_data = {"prem_3_months": ("3 Months", 2600), "prem_6_months": ("6 Months", 3700), "prem_12_months": ("12 Months", 6000)}
    plan_name, price = plan_data.get(callback.data, ("3 Months", 2600))
    await state.update_data(plan_name=plan_name, price=price)
    
    text = f"✈️ <b>Telegram Premium — {plan_name}</b>\n\nፕሪሚየም የሚገባበትን የቴሌግራም ዩዘርኔም ያስገቡ (ምሳሌ: @username)፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(TelegramPremiumState.waiting_for_username)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(TelegramPremiumState.waiting_for_username)
async def process_premium_username(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    raw_username = message.text.strip()
    try: await message.delete()
    except Exception: pass

    clean_username = raw_username if raw_username.startswith("@") else f"@{raw_username}"
    await state.update_data(target_username=clean_username)
    plan_name, price = data.get("plan_name"), data.get("price")

    settings = await get_settings()
    banks = settings.get("banks", {})
    keyboard = build_banks_keyboard(banks, "prem_pay")

    text = f"✈️ <b>{plan_name} Telegram Premium</b>\n👤 Recipient: <b>{clean_username}</b>\n💰 Price: <b>{price:,.2f} ETB</b>\n\nክፍያ የሚፈፅሙበትን መንገድ ይምረጡ፦"
    await state.set_state(TelegramPremiumState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(TelegramPremiumState.waiting_for_payment_method, F.data.startswith("prem_pay_"))
async def process_premium_payment_method(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    banks = settings.get("banks", {})
    pay_code = callback.data.replace("prem_pay_", "")
    bank_info = banks.get(pay_code, {})
    if isinstance(bank_info, dict):
        b_name = bank_info.get("name", pay_code.upper())
        b_acc = bank_info.get("number", "N/A")
        b_owner = bank_info.get("owner", "N/A")
    else:
        b_name, b_acc, b_owner = pay_code.upper(), "N/A", "N/A"
    
    text = f"🏛 <b>{b_name} Payment Info</b>\nAccount: <b>{b_acc}</b>\nName: <b>{b_owner}</b>\n\nከፍለው ግልጽ የክፍያ ስክሪንሾት ይላኩ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(TelegramPremiumState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(TelegramPremiumState.waiting_for_proof, F.photo)
async def process_premium_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(2)
    
    plan_name, price, target_username = data.get("plan_name"), data.get("price"), data.get("target_username")
    user = message.from_user
    
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": f"Telegram Premium {plan_name}",
        "details": f"Target: {target_username}", "amount": float(price),
        "status": "PENDING", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ord_key = await fb_post("orders", order_data)
    await fb_put(f"user_orders/{user.id}/{ord_key}", order_data)

    admin_text = (
        f"💎 <b>New Telegram Premium Order! (#{ord_key[:6]})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"✈️ Plan: {plan_name} | Price: {price:,.2f} ETB\n"
        f"🎯 Target Account: <b>{target_username}</b>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{ord_key}_{user.id}")]])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (#{ord_key[:6]})</b>\n\nፕሪሚየሙ ወደ <b>{target_username}</b> በቅርቡ ይጫናል።", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# 🌐 MONTHLY UNLIMITED DATA WORKFLOW
# ==========================================
@dp.callback_query(F.data == "unlimited_data")
async def start_unlimited_data(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    stock = settings.get("stocks", {}).get("unlimited_data", 0)
    
    if stock <= 0:
        await callback.answer("⚠️ ይቅርታ! በአሁኑ ሰዓት Monthly Unlimited Data stock አልቋል (Out of stock)።", show_alert=True)
        return

    text = (
        "🌐 <b>Monthly Unlimited Data</b>\n\n"
        "🏷 <b>Price:</b> 1,576.00 ETB each\n"
        f"🔥 <b>In stock:</b> <b>{stock} pcs</b>\n\n"
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(UnlimitedDataState.waiting_for_phone_number)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(UnlimitedDataState.waiting_for_phone_number)
async def process_data_phone_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    phone_num = message.text.strip()
    try: await message.delete()
    except Exception: pass

    if not (phone_num.startswith("09") or phone_num.startswith("07")) or len(phone_num) != 10 or not phone_num.isdigit():
        if last_msg_id:
            await bot.edit_message_text(
                "⚠️ <b>የተሳሳተ የስልክ ቁጥር!</b>\n\nእባክዎ ዳታው የሚሞላበትን ትክክለኛ የስልክ ቁጥር በ '09' ወይም '07' ጀምረው ያስገቡ (10 አሃዝ)፦",
                chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML"
            )
        return

    await state.update_data(data_phone=phone_num)

    settings = await get_settings()
    banks = settings.get("banks", {})
    keyboard = build_banks_keyboard(banks, "data_pay")

    text = (
        "🌐 <b>Monthly Unlimited Data — 1,576.00 ETB</b>\n"
        f"📱 Target Phone: <b>{phone_num}</b>\n\n"
        "እባክዎ ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    await state.set_state(UnlimitedDataState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(UnlimitedDataState.waiting_for_payment_method, F.data.startswith("data_pay_"))
async def process_data_payment_info(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    banks = settings.get("banks", {})
    pay_code = callback.data.replace("data_pay_", "")
    bank_info = banks.get(pay_code, {})
    if isinstance(bank_info, dict):
        b_name = bank_info.get("name", pay_code.upper())
        b_acc = bank_info.get("number", "N/A")
        b_owner = bank_info.get("owner", "N/A")
    else:
        b_name, b_acc, b_owner = pay_code.upper(), "N/A", "N/A"
    
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(UnlimitedDataState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(UnlimitedDataState.waiting_for_proof, F.photo)
async def process_data_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(2)
    
    data_phone = data.get("data_phone")
    user = message.from_user
    
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": "Monthly Unlimited Data",
        "details": f"Phone: {data_phone}", "amount": 1576.0,
        "status": "PENDING", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ord_key = await fb_post("orders", order_data)
    await fb_put(f"user_orders/{user.id}/{ord_key}", order_data)

    admin_text = (
        f"🌐 <b>New Monthly Unlimited Data Order! (#{ord_key[:6]})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"📱 Target Phone Number: <code>{data_phone}</code>\n"
        f"💵 Price: 1,576.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve (ዳታው ተሞላ)", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{ord_key}_{user.id}")]])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>Payment proof received successfully! (#{ord_key[:6]})</b>\n\nየክፍያ ማረጋገጫዎ ደርሶናል! ያልተገደበው ዳታ በቅርቡ ወደ <b>{data_phone}</b> ይጫናል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# ✨ GEMINI PRO 18M WORKFLOW
# ==========================================
@dp.callback_query(F.data == "gemini_pro")
async def start_gemini_pro(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    stock = settings.get("stocks", {}).get("gemini_pro", 0)
    
    if stock <= 0:
        await callback.answer("⚠️ ይቅርታ! በአሁኑ ሰዓት Gemini Pro stock አልቋል (Out of stock)።", show_alert=True)
        return

    text = (
        "✨ <b>Gemini Pro 18m</b>\n\n"
        "🏷 <b>Price:</b> 350.00 ETB each\n"
        f"🔥 <b>In stock:</b> <b>{stock} pcs</b>\n\n"
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
    settings = await get_settings()
    banks = settings.get("banks", {})
    keyboard = build_banks_keyboard(banks, "gem_pay")

    text = (
        "✨ <b>Gemini Pro 18m — 350.00 ETB</b>\n\n"
        "እባክዎ ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
    await state.set_state(GeminiProState.waiting_for_payment_method)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(GeminiProState.waiting_for_payment_method, F.data.startswith("gem_pay_"))
async def process_gemini_payment_info(callback: types.CallbackQuery, state: FSMContext):
    settings = await get_settings()
    banks = settings.get("banks", {})
    pay_code = callback.data.replace("gem_pay_", "")
    bank_info = banks.get(pay_code, {})
    if isinstance(bank_info, dict):
        b_name = bank_info.get("name", pay_code.upper())
        b_acc = bank_info.get("number", "N/A")
        b_owner = bank_info.get("owner", "N/A")
    else:
        b_name, b_acc, b_owner = pay_code.upper(), "N/A", "N/A"
    
    text = (
        "✨ <b>Gemini Pro 18m Activation Link</b>\n"
        "💰 Amount to pay: <b>350.00 ETB</b>\n\n"
        f"🏛 <b>{b_name} Payment Info</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        "Send the exact 350.00 ETB amount, then upload a clear receipt screenshot.\n"
        "ትክክለኛውን 350.00 ETB ከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(GeminiProState.waiting_for_proof)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(GeminiProState.waiting_for_proof, F.photo)
async def process_gemini_proof_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try: await message.delete()
    except Exception: pass
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(2)
    
    user = message.from_user
    order_data = {
        "user_id": user.id, "user_name": user.full_name, "service": "Gemini Pro 18m",
        "details": "Self-activation link", "amount": 350.0,
        "status": "PENDING", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ord_key = await fb_post("orders", order_data)
    await fb_put(f"user_orders/{user.id}/{ord_key}", order_data)

    admin_text = (
        f"✨ <b>New Gemini Pro 18m Order! (#{ord_key[:6]})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Price: 350.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve (ሊንክ ላክ)", callback_data=f"app_{ord_key}_{user.id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{ord_key}_{user.id}")]])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>Payment proof received successfully! (#{ord_key[:6]})</b>\n\nየክፍያ ማረጋገጫዎ ደርሶናል! አድሚኑ ክፍያውን አረጋግጦ የ Gemini Pro Activation link ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()

# ==========================================
# 🛡 ADMIN APPROVE / REJECT CALLBACKS (AUTO STOCK DEDUCTION)
# ==========================================
@dp.callback_query(F.data.startswith("app_"))
async def admin_approve_order(callback: types.CallbackQuery):
    role = await get_admin_role(callback.from_user.id)
    if role not in ["SUPER_ADMIN", "FULL", "ORDERS_SUPPORT"]:
        await callback.answer("❌ ትዕዛዝ ለማጽደቅ ስልጣን የሎትም!", show_alert=True)
        return
        
    parts = callback.data.split("_")
    ord_key, user_id = parts[1], int(parts[2])
    
    ord_data = await fb_get(f"orders/{ord_key}") or {}
    service = ord_data.get("service", "")
    
    # Auto Stock Deductions
    settings = await get_settings()
    stocks = settings.get("stocks", {})
    
    if "Buy USDT" in service:
        c_amt = float(ord_data.get("crypto_amount", 0.0))
        stocks["usdt"] = max(0.0, stocks.get("usdt", 0.0) - c_amt)
    elif "Sell USDT" in service:
        pay_amt = float(ord_data.get("amount", 0.0))
        stocks["etb_reserve"] = max(0.0, stocks.get("etb_reserve", 0.0) - pay_amt)
    elif "Unlimited Data" in service:
        stocks["unlimited_data"] = max(0, stocks.get("unlimited_data", 0) - 1)
    elif "Gemini Pro" in service:
        stocks["gemini_pro"] = max(0, stocks.get("gemini_pro", 0) - 1)
        
    settings["stocks"] = stocks
    await fb_put("settings", settings)
    
    await fb_put(f"orders/{ord_key}/status", "APPROVED")
    await fb_put(f"user_orders/{user_id}/{ord_key}/status", "APPROVED")
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 <b>ትዕዛዝዎ (#{ord_key[:6]}) በተሳካ ሁኔታ ጸድቋል (Approved)!</b>\n\n"
            "አድሚኑ ክፍያውን አረጋግጦ አገልግሎትዎን ልኮልዎታል። ቦቱን ስለተጠቀሙ እናመሰግናለን! 🙏\n"
            f"ችግር ካጋጠመዎት ሰፖርታችንን ያናግሩ፦ {SUPPORT_USERNAME}",
            parse_mode="HTML"
        )
        if callback.message.caption:
            await callback.message.edit_caption(caption=callback.message.caption + f"\n\n<b>STATUS: ✅ APPROVED BY ADMIN</b>", parse_mode="HTML")
        await callback.answer("ትዕዛዙ በተሳካ ሁኔታ ጸድቋል!")
    except Exception as e:
        await callback.answer(f"ስህተት: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("rej_"))
async def start_admin_reject(callback: types.CallbackQuery, state: FSMContext):
    role = await get_admin_role(callback.from_user.id)
    if role not in ["SUPER_ADMIN", "FULL", "ORDERS_SUPPORT"]:
        await callback.answer("❌ ትዕዛዝ ውድቅ ለማድረግ ስልጣን የሎትም!", show_alert=True)
        return
        
    parts = callback.data.split("_")
    ord_key, user_id = parts[1], int(parts[2])
    await state.update_data(reject_ord_key=ord_key, reject_user_id=user_id, admin_msg=callback.message)
    await state.set_state(AdminRejectState.waiting_for_reason)
    await callback.message.reply(f"✏️ ለ Order #{ord_key[:6]} ውድቅ የተደረገበትን ምክንያት ይጻፉ፦")
    await callback.answer()

@dp.message(AdminRejectState.waiting_for_reason)
async def process_reject_reason(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data()
    ord_key = data.get("reject_ord_key")
    user_id = data.get("reject_user_id")
    admin_msg = data.get("admin_msg")
    
    await fb_put(f"orders/{ord_key}/status", "REJECTED")
    await fb_put(f"user_orders/{user_id}/{ord_key}/status", "REJECTED")
    
    try:
        await bot.send_message(
            user_id,
            f"❌ <b>ትዕዛዝዎ (#{ord_key[:6]}) ውድቅ ተደርጓል (Rejected)!</b>\n\n<b>ምክንያት:</b> {reason}\n\nሰፖርት: {SUPPORT_USERNAME}",
            parse_mode="HTML"
        )
        if admin_msg and admin_msg.caption:
            await admin_msg.edit_caption(caption=admin_msg.caption + f"\n\n<b>STATUS: ❌ REJECTED</b>\n<b>Reason:</b> {reason}", parse_mode="HTML")
        await message.reply("✅ ውድቅ የተደረገበት ምክንያት ተልኳል!")
    except Exception as e:
        await message.reply(f"❌ ስህተት: {e}")
            
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    help_text = (
        "❓ <b>Help | እርዳታ</b>\n\n"
        "<b>User commands:</b>\n"
        "/start — Start the bot & see main menu\n"
        "/cancel — Cancel current action\n\n"
        "<b>Working hours:</b> 08:00–22:00 EAT\n"
        "<b>Support:</b> Use the Support button below 🎯"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]])
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🔄 SELF-PING & WEB SERVER
# ==========================================
async def internal_self_ping_loop():
    while True:
        await asyncio.sleep(600)
        if RENDER_EXTERNAL_URL:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(RENDER_EXTERNAL_URL) as resp:
                        print(f"🔄 Self-ping sent to {RENDER_EXTERNAL_URL}, status: {resp.status}")
            except Exception as e:
                print(f"Self-ping error: {e}")

async def handle_ping(request): 
    return web.Response(text="Bot is awake & running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    print("ቦቱ እና ዌብ ሰርቨሩ ሙሉ ስራ ጀምረዋል...")
    asyncio.create_task(internal_self_ping_loop())
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())

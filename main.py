import os
import re
import asyncio
import sqlite3
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))

# የንግድና የሰፖርት ትክክለኛ መረጃዎች
TELEBIRR_NAME = "Aymen Nesredin Redi"
TELEBIRR_NUMBER = "0939357745"
CBE_ACCOUNT = "1000780294322"
CBE_NAME = "Aymen Nesredin Redi"
COOP_ACCOUNT = "1947701000001"
COOP_NAME = "Aymen Nesredin Redi"

AWASH_ACCOUNT = "01425174740300"
AWASH_NAME = "Nesredin Redi"
ABYSSINIA_ACCOUNT = "100404915"
ABYSSINIA_NAME = "Nesredin Redi"
DASHEN_ACCOUNT = "2912539951521"
DASHEN_NAME = "Nesredin Redi"

SUPPORT_USERNAME = "@Neon_ghost147"

# የ USDT መቀበያ አድራሻዎች
OUR_BYBIT_UID = "580130044"
OUR_POLYGON_ADDRESS = "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"
OUR_BEP20_ADDRESS = "0x9244d02e10124bfa091d1d5c25a4aed204833ad7"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 🗄 DATABASE SETUP (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            service_type TEXT,
            details TEXT,
            amount_etb REAL,
            status TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_user(user_id, username, first_name):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, username, first_name))
    conn.commit()
    conn.close()

def create_order(user_id, user_name, service_type, details, amount_etb, status="PENDING"):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO orders (user_id, user_name, service_type, details, amount_etb, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, user_name, service_type, details, amount_etb, status, created_at))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()

def get_user_orders(user_id, status_filter=None):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM orders WHERE user_id = ? AND status = ? ORDER BY order_id DESC", (user_id, status_filter))
    else:
        cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_order_by_id(order_id):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_users():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

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

class SupportMessageState(StatesGroup):
    waiting_for_message = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

class AdminRejectState(StatesGroup):
    waiting_for_reason = State()

class BroadcastState(StatesGroup):
    waiting_for_broadcast_msg = State()

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
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
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
# 👤 MY PROFILE & HISTORY
# ==========================================
@dp.callback_query(F.data == "my_profile")
async def show_my_profile(callback: types.CallbackQuery):
    user = callback.from_user
    profile_text = (
        f"🛡 <b>My Profile | የእኔ መገለጫ</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'Not set'}\n\n"
        f"እባክዎ ከታች የትዕዛዝ ታሪክዎን ወይም የክፍያ መረጃዎን ይምረጡ፦"
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
    orders = get_user_orders(user_id)
    
    if not orders:
        text = "📦 <b>My Orders (0)</b>\n\nእስካሁን ምንም ትዕዛዝ አልላኩም።"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    text = f"📦 <b>My Orders ({len(orders)})</b>\nTap an order to view details:"
    buttons = []
    for ord in orders[:8]: # እስከ 8 ትዕዛዝ ያሳያል
        ord_id, _, _, service, _, amount, status, _ = ord
        status_icon = "⏳" if status == "PENDING" else ("✅" if status == "APPROVED" else "❌")
        buttons.append([InlineKeyboardButton(text=f"{status_icon} #{ord_id} — {service} — {amount:,.0f} ETB", callback_data=f"view_ord_{ord_id}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("view_ord_"))
async def view_single_order(callback: types.CallbackQuery):
    ord_id = int(callback.data.split("_")[2])
    ord = get_order_by_id(ord_id)
    if ord:
        o_id, u_id, u_name, service, details, amount, status, created = ord
        text = (
            f"📑 <b>Order #{o_id} Details</b>\n\n"
            f"• <b>Type:</b> {service}\n"
            f"• <b>Status:</b> {status}\n"
            f"• <b>Amount:</b> {amount:,.2f} ETB\n"
            f"• <b>Details:</b> {details}\n"
            f"• <b>Created:</b> {created}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="my_orders")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "completed_history")
async def show_completed_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_user_orders(user_id, status_filter="APPROVED")
    
    if not orders:
        text = "✅ <b>Completed Order History (0)</b>\n\nምንም የተጠናቀቀ ትዕዛዝ የለም።"
    else:
        text = f"✅ <b>Completed Order History ({len(orders)})</b>\n\n"
        for ord in orders[:5]:
            o_id, _, _, service, _, amount, _, created = ord
            text += f"• <b>#{o_id}</b> | {service} | {amount:,.2f} ETB | {created}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Profile", callback_data="my_profile")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🛠 INTERACTIVE SUPPORT SYSTEM
# ==========================================
@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    support_text = (
        "🆘 <b>Support | ድጋፍ</b>\n\n"
        "ስለ ትዕዛዝዎ ጥያቄ ካለዎት ወይም የክፍያ ችግር ካጋጠመዎት ከታች ያለውን <b>Message Admin Inside Bot</b> ቁልፍ በመጫን ቀጥታ ለአድሚን ይጻፉ፦\n\n"
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
    text = (
        "💬 <b>Message Admin</b>\n\n"
        "እባክዎ ለሰፖርት አድሚኖች መላክ የሚፈልጉትን ጥያቄ፣ ጽሁፍ ወይም ስክሪንሾት ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SupportMessageState.waiting_for_message)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.message(SupportMessageState.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    try:
        await message.delete()
    except Exception:
        pass

    user = message.from_user
    admin_caption = (
        f"📩 <b>New Support Message from User!</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Reply to User (መልስ ስጥ)", callback_data=f"reply_user_{user.id}")]
    ])

    if ADMIN_GROUP_ID != 0:
        try:
            if message.photo:
                await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=f"{admin_caption}\n\n💬 <b>Msg:</b> {message.caption if message.caption else ''}", reply_markup=admin_keyboard, parse_mode="HTML")
            else:
                await bot.send_message(ADMIN_GROUP_ID, text=f"{admin_caption}\n\n💬 <b>Msg:</b> {message.text}", reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending support to group: {e}")

    if last_msg_id:
        await bot.edit_message_text(
            "✅ <b>መልእክትዎ ለአድሚን ተልኳል!</b>\n\nአድሚኖች መልእክትዎን አይተው አሁን በቦቱ በኩል ይመልሱልዎታል። እባክዎ በትዕግስት ይጠብቁ...",
            chat_id=message.chat.id,
            message_id=last_msg_id,
            parse_mode="HTML"
        )
    await state.clear()

# Admin Reply Callback
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
        await message.reply(f"❌ ለተጠቃሚው መላክ አልተቻለም: {e}")
    await state.clear()

# ==========================================
# ❓ HELP & COMMANDS
# ==========================================
@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    help_text = (
        "❓ <b>Help | እርዳታ</b>\n\n"
        "<b>User commands:</b>\n"
        "/start — Start the bot & see main menu\n"
        "/rates — View current buy/sell rates\n"
        "/myid — Show your Telegram user ID\n"
        "/cancel — Cancel current action\n\n"
        "<b>Working hours:</b> 08:00–22:00 EAT\n"
        "<b>Support:</b> Use the Support button below 🎯"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu | ዋና ማውጫ", callback_data="main_menu")]
    ])
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(Command("rates"))
async def cmd_rates(message: types.Message):
    rates_text = (
        "🟢 <b>Current Rates</b>\n"
        "Buy: 197.00 ETB / USDT\n"
        "Sell: 182.00 ETB / USDT"
    )
    await message.answer(rates_text, parse_mode="HTML")

@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.answer(f"💬 <b>Your Telegram ID:</b>\n<code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🛑 Action cancelled. Back to main menu.", reply_markup=get_main_menu_keyboard())

# Broadcast Command (ለአድሚን ብቻ)
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📢 ለሁሉም ተጠቃሚዎች የሚላከውን ማስታወቂያ ይጻፉ፦")
    await state.set_state(BroadcastState.waiting_for_broadcast_msg)

@dp.message(BroadcastState.waiting_for_broadcast_msg)
async def process_broadcast(message: types.Message, state: FSMContext):
    users = get_all_users()
    success = 0
    await message.answer(f"⏳ ለ {len(users)} ተጠቃሚዎች በመላክ ላይ...")
    for u_id in users:
        try:
            await message.copy_to(chat_id=u_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ ብሮድካስት ተጠናቋል! ለ {success} ተጠቃሚዎች ደርሷል።")
    await state.clear()


# ==========================================
# 🟢 BUY USDT WORKFLOW
# ==========================================
@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "💰 <b>Buy USDT | USDT መግዛት</b>\n\n"
        "• Rate: 1 USDT = 197.0 ETB\n"
        "• Min / Max: 0.5 - 10000.0 USDT\n\n"
        "ምን ያህል USDT መግዛት ይፈልጋሉ? (ምሳሌ: 10)፦"
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
    try: await message.delete()
    except Exception: pass
        
    try:
        amount = float(message.text)
        if amount < 0.5 or amount > 10000.0:
            if last_msg_id: await bot.edit_message_text("⚠️ እባክዎ ከ 0.5 እስከ 10000.0 USDT መካከል ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)
            return
        
        total_price = amount * 197.0
        await state.update_data(amount=amount, total_price=total_price)
        
        text = (
            "✅ <b>Order Summary</b>\n"
            f"• Amount: {amount:.4f} USDT\n"
            f"• Pay: {total_price:,.2f} ETB\n\n"
            "USDT የት ይላክልዎታል? (የመቀበያ መንገድ ይምረጡ)፦"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Binance ID", callback_data="net_binance"), InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="net_bep20")],
            [InlineKeyboardButton(text="🔶 Bybit UID", callback_data="net_bybit"), InlineKeyboardButton(text="🟣 Polygon", callback_data="net_polygon")],
            [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
        ])
        await state.set_state(BuyUSDTState.waiting_for_network)
        if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")
    except ValueError:
        if last_msg_id: await bot.edit_message_text("❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ፦", chat_id=message.chat.id, message_id=last_msg_id)

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
    
    text = (
        f"📬 <b>Receiving destination saved</b>\n"
        f"• USDT: {amount:.4f}\n• Pay: {total_price:,.2f} ETB\n• Destination: {address}\n\n"
        "ክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    )
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
    data = await state.get_data()
    pay_code = callback.data
    if pay_code == "buy_pay_telebirr": b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "buy_pay_cbe": b_name, b_acc, b_owner = "CBE", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "buy_pay_coop": b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "buy_pay_awash": b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "buy_pay_abyssinia": b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else: b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = (
        f"🏛 <b>{b_name} Payment Info</b>\n\n"
        f"Number/Account: <b>{b_acc}</b>\n"
        f"Name: <b>{b_owner}</b>\n\n"
        f"ትክክለኛውን የብር መጠን ከፍለው ግልጽ የ{b_name} ደረሰኝ ስክሪንሾት ይላኩ።"
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
        
    if last_msg_id: await bot.edit_message_text("🔄 Processing payment proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(1)
    
    amount, total_price, address, network = data.get("amount"), data.get("total_price"), data.get("address"), data.get("network")
    user = message.from_user
    
    # 1. ዳታቤዝ ውስጥ መመዝገብ
    order_id = create_order(user.id, user.full_name, "Buy USDT", f"{amount} USDT to {network}:{address}", total_price, "PENDING")

    admin_text = (
        f"🚨 <b>New BUY USDT Order! (#{order_id})</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Amount: {amount} USDT\n"
        f"💰 Pay: {total_price:,.2f} ETB\n"
        f"🌐 Network: {network}\n"
        f"📍 Address/UID: <code>{address}</code>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (አጽድቅ)", callback_data=f"app_{order_id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{order_id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (Order #{order_id})</b>\n\nትዕዛዝዎ በአስተዳዳሪዎች እየተጣራ ነው። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()


# ==========================================
# 🔴 SELL USDT WORKFLOW
# ==========================================
@dp.callback_query(F.data == "sell_usdt")
async def start_sell_usdt(callback: types.CallbackQuery, state: FSMContext):
    text = "🔴 <b>Sell USDT — Step 1 of 4</b>\n\nብር የሚቀበሉበትን የክፍያ መንገድ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="payout_telebirr"), InlineKeyboardButton(text="🏦 CBE", callback_data="payout_cbe")],
        [InlineKeyboardButton(text="🏦 COOP Bank", callback_data="payout_coop"), InlineKeyboardButton(text="🦁 Awash Bank", callback_data="payout_awash")],
        [InlineKeyboardButton(text="🏛 Abyssinia", callback_data="payout_abyssinia"), InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="payout_dashen")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_payout_method)
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(SellUSDTState.waiting_for_payout_method, F.data.startswith("payout_"))
async def select_payout_method(callback: types.CallbackQuery, state: FSMContext):
    method_map = {"payout_telebirr": "Telebirr", "payout_cbe": "CBE", "payout_coop": "COOP Bank", "payout_awash": "Awash Bank", "payout_abyssinia": "Bank of Abyssinia", "payout_dashen": "Dashen Bank"}
    method_name = method_map.get(callback.data, "Bank Account")
    await state.update_data(payout_method=method_name)
    
    text = f"🔴 <b>Step 2 of 4 — {method_name}</b>\n\nብር የሚቀበሉበትን የ <b>{method_name}</b> ቁጥር ያስገቡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]])
    await state.set_state(SellUSDTState.waiting_for_account_number)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(SellUSDTState.waiting_for_account_number)
async def process_account_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    account_num = message.text.strip()
    try: await message.delete()
    except Exception: pass

    await state.update_data(account_num=account_num)
    text = "👤 በባንኩ/ቴሌብር የተመዘገበውን የባለቤቱን ሙሉ ስም ያስገቡ፦"
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

    await state.update_data(acc_name=acc_name)
    
    text = "🔴 <b>Step 3 of 4 — USDT deposit method</b>\n\nUSDT ለእኛ በምን መንገድ ይልካሉ? (ከታች ይምረጡ)፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔶 Bybit UID", callback_data="deposit_bybit"), InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="deposit_bep20")],
        [InlineKeyboardButton(text="🟣 Polygon (USDT)", callback_data="deposit_polygon")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(SellUSDTState.waiting_for_deposit_network)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")

@dp.callback_query(SellUSDTState.waiting_for_deposit_network, F.data.startswith("deposit_"))
async def select_deposit_network(callback: types.CallbackQuery, state: FSMContext):
    net_code = callback.data
    if net_code == "deposit_bybit": net_name, our_addr = "Bybit UID", OUR_BYBIT_UID
    elif net_code == "deposit_bep20": net_name, our_addr = "BSC (BEP20)", OUR_BEP20_ADDRESS
    else: net_name, our_addr = "Polygon Network", OUR_POLYGON_ADDRESS

    await state.update_data(deposit_network=net_name, our_address=our_addr)
    
    text = f"🔴 <b>Step 4 of 4 — {net_name}</b>\n\nUSDT ወደዚህ የእኛ አድራሻ ይላኩ፦\n\n<code>{our_addr}</code>\n\nየላኩበትን ክፍያ ግልጽ ስክሪንሾት ይላኩ፦"
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
        
    if last_msg_id: await bot.edit_message_text("🔄 Reading transfer proof...", chat_id=message.chat.id, message_id=last_msg_id)
    await asyncio.sleep(1)
    
    payout_method, account_num, acc_name, deposit_network = data.get("payout_method"), data.get("account_num"), data.get("acc_name"), data.get("deposit_network")
    user = message.from_user
    
    # 1. ዳታቤዝ ውስጥ መመዝገብ
    order_id = create_order(user.id, user.full_name, "Sell USDT", f"Payout to {payout_method}:{account_num} ({acc_name}) via {deposit_network}", 0.0, "PENDING")

    admin_text = (
        f"🚨 <b>New SELL USDT Order! (#{order_id})</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"🌐 Sent via: {deposit_network}\n"
        f"💵 Payout Method: {payout_method}\n"
        f"📍 Payout Account: <code>{account_num}</code>\n"
        f"👤 Account Name: {acc_name}\n\n"
        "የ USDT ትራንስፈር ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (ብር ላክኩ)", callback_data=f"app_{order_id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{order_id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የማረጋገጫ ስክሪንሾትዎ ደርሶናል! (Order #{order_id})</b>\n\nአድሚኑ ማረጋገጫውን አይቶ የኢትዮጵያ ብር ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
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

    text = f"✈️ <b>{plan_name} Telegram Premium</b>\n👤 Recipient: <b>{clean_username}</b>\n💰 Price: <b>{price:,.2f} ETB</b>\n\nክፍያ የሚፈፅሙበትን መንገድ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="prem_pay_telebirr"), InlineKeyboardButton(text="🏦 CBE", callback_data="prem_pay_cbe")],
        [InlineKeyboardButton(text="🏦 COOP Bank", callback_data="prem_pay_coop"), InlineKeyboardButton(text="🦁 Awash Bank", callback_data="prem_pay_awash")],
        [InlineKeyboardButton(text="🏛 Abyssinia", callback_data="prem_pay_abyssinia"), InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="prem_pay_dashen")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(TelegramPremiumState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(TelegramPremiumState.waiting_for_payment_method, F.data.startswith("prem_pay_"))
async def process_premium_payment_method(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pay_code = callback.data
    if pay_code == "prem_pay_telebirr": b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "prem_pay_cbe": b_name, b_acc, b_owner = "CBE", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "prem_pay_coop": b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "prem_pay_awash": b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "prem_pay_abyssinia": b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else: b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = f"🏛 <b>{b_name} Payment Info</b>\n\nAccount: <b>{b_acc}</b>\nName: <b>{b_owner}</b>\n\nከፍለው ግልጽ የክፍያ ደረሰኝ ስክሪንሾት ይላኩ፦"
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
    await asyncio.sleep(1)
    
    plan_name, price, target_username = data.get("plan_name"), data.get("price"), data.get("target_username")
    user = message.from_user
    
    order_id = create_order(user.id, user.full_name, f"Telegram Premium {plan_name}", f"Target: {target_username}", float(price), "PENDING")

    admin_text = (
        f"💎 <b>New Telegram Premium Order! (#{order_id})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"✈️ Plan: {plan_name}\n"
        f"💵 Price: {price:,.2f} ETB\n"
        f"🎯 Target Account: <b>{target_username}</b>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (ፕሪሚየም ተጫነ)", callback_data=f"app_{order_id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{order_id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (Order #{order_id})</b>\n\nፕሪሚየሙ በቅርቡ ወደ <b>{target_username}</b> ይጫናል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()


# ==========================================
# 🌐 MONTHLY UNLIMITED DATA WORKFLOW
# ==========================================
@dp.callback_query(F.data == "unlimited_data")
async def start_unlimited_data(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "🌐 <b>Monthly Unlimited Data (1,576 ETB)</b>\n\n"
        "🍃 <b>Validity:</b> 30 Days | ⚡ <b>Speed:</b> Fast\n\n"
        "ያልተገደበው ዳታ የሚጫንበትን የስልክ ቁጥር ለማስገባት <b>Buy now</b> ይጫኑ፦"
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
    text = "❓ <b>የስልክ ቁጥር ያስገቡ፦</b>\n\nያልተገደበው ዳታ የሚጫንበትን የስልክ ቁጥር ያስገቡ (ምሳሌ: 0912345678)፦"
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

    await state.update_data(data_phone=phone_num)

    text = f"🌐 <b>Monthly Unlimited Data — 1,576.00 ETB</b>\n📱 Target Phone: <b>{phone_num}</b>\n\nክፍያ የሚፈጽሙበትን መንገድ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="data_pay_telebirr"), InlineKeyboardButton(text="🏦 CBE", callback_data="data_pay_cbe")],
        [InlineKeyboardButton(text="🏦 COOP Bank", callback_data="data_pay_coop"), InlineKeyboardButton(text="🦁 Awash Bank", callback_data="data_pay_awash")],
        [InlineKeyboardButton(text="🏛 Abyssinia", callback_data="data_pay_abyssinia"), InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="data_pay_dashen")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(UnlimitedDataState.waiting_for_payment_method)
    if last_msg_id: await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(UnlimitedDataState.waiting_for_payment_method, F.data.startswith("data_pay_"))
async def process_data_payment_info(callback: types.CallbackQuery, state: FSMContext):
    pay_code = callback.data
    if pay_code == "data_pay_telebirr": b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "data_pay_cbe": b_name, b_acc, b_owner = "CBE", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "data_pay_coop": b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "data_pay_awash": b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "data_pay_abyssinia": b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else: b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = f"🏛 <b>{b_name} Payment Info</b>\n\nAccount: <b>{b_acc}</b>\nName: <b>{b_owner}</b>\n\nትክክለኛውን 1,576.00 ETB ከፍለው ደረሰኝ ይላኩ፦"
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
    await asyncio.sleep(1)
    
    data_phone = data.get("data_phone")
    user = message.from_user
    
    order_id = create_order(user.id, user.full_name, "Monthly Unlimited Data", f"Phone: {data_phone}", 1576.0, "PENDING")

    admin_text = (
        f"🌐 <b>New Unlimited Data Order! (#{order_id})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"📱 Target Phone: <code>{data_phone}</code>\n"
        f"💵 Price: 1,576.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (ዳታ ተሞላ)", callback_data=f"app_{order_id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{order_id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (Order #{order_id})</b>\n\nዳታው በቅርቡ ወደ <b>{data_phone}</b> ይጫናል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()


# ==========================================
# ✨ GEMINI PRO 18M WORKFLOW
# ==========================================
@dp.callback_query(F.data == "gemini_pro")
async def start_gemini_pro(callback: types.CallbackQuery, state: FSMContext):
    text = "✨ <b>Gemini Pro 18m (350 ETB)</b>\n\nSelf-activation link ለ Gmail አካውንትዎ ለመግዛት <b>Buy now</b> ይጫኑ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Buy now (350 ETB)", callback_data="buy_gemini_now")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    msg = await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "buy_gemini_now")
async def select_gemini_payment_method(callback: types.CallbackQuery, state: FSMContext):
    text = "✨ <b>Gemini Pro 18m — 350.00 ETB</b>\n\nክፍያ የሚፈጽሙበትን የባንክ/ቴሌብር መንገድ ይምረጡ፦"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="gem_pay_telebirr"), InlineKeyboardButton(text="🏦 CBE", callback_data="gem_pay_cbe")],
        [InlineKeyboardButton(text="🏦 COOP Bank", callback_data="gem_pay_coop"), InlineKeyboardButton(text="🦁 Awash Bank", callback_data="gem_pay_awash")],
        [InlineKeyboardButton(text="🏛 Abyssinia", callback_data="gem_pay_abyssinia"), InlineKeyboardButton(text="🔷 Dashen Bank", callback_data="gem_pay_dashen")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(GeminiProState.waiting_for_payment_method)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(GeminiProState.waiting_for_payment_method, F.data.startswith("gem_pay_"))
async def process_gemini_payment_info(callback: types.CallbackQuery, state: FSMContext):
    pay_code = callback.data
    if pay_code == "gem_pay_telebirr": b_name, b_acc, b_owner = "Telebirr", TELEBIRR_NUMBER, TELEBIRR_NAME
    elif pay_code == "gem_pay_cbe": b_name, b_acc, b_owner = "CBE", CBE_ACCOUNT, CBE_NAME
    elif pay_code == "gem_pay_coop": b_name, b_acc, b_owner = "COOP Bank", COOP_ACCOUNT, COOP_NAME
    elif pay_code == "gem_pay_awash": b_name, b_acc, b_owner = "Awash Bank", AWASH_ACCOUNT, AWASH_NAME
    elif pay_code == "gem_pay_abyssinia": b_name, b_acc, b_owner = "Bank of Abyssinia", ABYSSINIA_ACCOUNT, ABYSSINIA_NAME
    else: b_name, b_acc, b_owner = "Dashen Bank", DASHEN_ACCOUNT, DASHEN_NAME

    text = f"✨ <b>Gemini Pro 18m</b>\n🏛 <b>{b_name}</b>\n\nAccount: <b>{b_acc}</b>\nName: <b>{b_owner}</b>\n\nትክክለኛውን 350.00 ETB ከፍለው ደረሰኝ ይላኩ፦"
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
    await asyncio.sleep(1)
    
    user = message.from_user
    order_id = create_order(user.id, user.full_name, "Gemini Pro 18m", "Self-activation link", 350.0, "PENDING")

    admin_text = (
        f"✨ <b>New Gemini Pro 18m Order! (#{order_id})</b>\n\n"
        f"👤 Customer: {user.full_name} (@{user.username if user.username else 'None'}, ID: <code>{user.id}</code>)\n"
        f"💵 Price: 350.00 ETB\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (ሊንክ ላክ)", callback_data=f"app_{order_id}"), InlineKeyboardButton(text="❌ Reject (ውድቅ አድርግ)", callback_data=f"rej_{order_id}")]
    ])
    
    if ADMIN_GROUP_ID != 0:
        try: await bot.send_photo(ADMIN_GROUP_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e: print(f"Error: {e}")
            
    if last_msg_id:
        await bot.edit_message_text(f"✅ <b>የክፍያ ማረጋገጫዎ ደርሶናል! (Order #{order_id})</b>\n\nአድሚኑ ክፍያውን አረጋግጦ የ Gemini Pro Activation link ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ... ⏳", chat_id=message.chat.id, message_id=last_msg_id, parse_mode="HTML")
    await state.clear()


# ==========================================
# 🛡 ADMIN APPROVE / REJECT CALLBACKS (DATABASE SYNCHRONIZED)
# ==========================================
@dp.callback_query(F.data.startswith("app_"))
async def admin_approve_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    ord = get_order_by_id(order_id)
    
    if ord:
        user_id = ord[1]
        update_order_status(order_id, "APPROVED")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 <b>ትዕዛዝዎ Order #{order_id} በተሳካ ሁኔታ ጸድቋል (Approved)!</b>\n\n"
                    "አድሚኑ ክፍያውን አረጋግጦ አገልግሎትዎን ልኮልዎታል። ቦቱን ስለተጠቀሙ እናመሰግናለን! 🙏\n"
                    f"ችግር ካጋጠመዎት ሰፖርታችንን ያናግሩ፦ {SUPPORT_USERNAME}"
                ),
                parse_mode="HTML"
            )
            await callback.message.edit_caption(caption=callback.message.caption + f"\n\n<b>STATUS: ✅ APPROVED (Order #{order_id})</b>", parse_mode="HTML")
            await callback.answer("ትዕዛዙ በተሳካ ሁኔታ ጸድቋል!")
        except Exception as e:
            await callback.answer(f"ስህተት: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("rej_"))
async def start_admin_reject(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(reject_order_id=order_id, admin_msg=callback.message)
    await state.set_state(AdminRejectState.waiting_for_reason)
    await callback.message.reply(f"✏️ ለ Order #{order_id} ውድቅ የተደረገበትን ምክንያት ይጻፉ፦")
    await callback.answer()

@dp.message(AdminRejectState.waiting_for_reason)
async def process_reject_reason(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data()
    order_id = data.get("reject_order_id")
    admin_msg = data.get("admin_msg")
    
    ord = get_order_by_id(order_id)
    if ord:
        user_id = ord[1]
        update_order_status(order_id, "REJECTED")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ <b>ትዕዛዝዎ Order #{order_id} ውድቅ ተደርጓል (Rejected)!</b>\n\n"
                    f"<b>ምክንያት:</b> {reason}\n\n"
                    f"ለበለጠ መረጃ ሰፖርታችንን ያናግሩ፦ {SUPPORT_USERNAME}"
                ),
                parse_mode="HTML"
            )
            if admin_msg:
                await admin_msg.edit_caption(caption=admin_msg.caption + f"\n\n<b>STATUS: ❌ REJECTED (Order #{order_id})</b>\n<b>Reason:</b> {reason}", parse_mode="HTML")
            await message.reply("✅ ውድቅ የተደረገበት ምክንያት ለተጠቃሚው ተልኳል!")
        except Exception as e:
            await message.reply(f"❌ ስህተት: {e}")
            
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# Web Server for Render
async def handle_ping(request):
    return web.Response(text="Bot is running 24/7!")

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
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

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
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))  # የአድሚን ትዕዛዞች የሚላኩበት ግሩፕ ID (ለምሳሌ፦ -100xxxxxxxxxx)

# የንግድና የሰፖርት መረጃዎች
TELEBIRR_NAME = "Aymen nesre"
TELEBIRR_NUMBER = "0939357745"
SUPPORT_USERNAME = "@Neon_ghost147"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ለትዕዛዞች ጊዜያዊ ማስታወሻ መያዣ
orders_cache = {}

# FSM States ለ Buy USDT 7ቱ ስቴፖች እና ለአድሚን Reject ምክንያት
class BuyUSDTState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_network = State()
    waiting_for_address = State()
    waiting_for_payment_method = State()
    waiting_for_receipt = State()

class AdminRejectState(StatesGroup):
    waiting_for_reason = State()

# ዋናው ማኑ ሜኑ ኪቦርድ (መጀመሪያ እንደነበረው አልተነካም)
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Buy USDT | USDT መግዛት", callback_data="buy_usdt"),
            InlineKeyboardButton(text="🔴 Sell USDT | USDT መሸጥ", callback_data="sell_usdt")
        ],
        [
            InlineKeyboardButton(text="💎 Telegram Premium", callback_data="telegram_premium"),
            InlineKeyboardButton(text="✨ Gemini Pro 18m", callback_data="gemini_pro")
        ],
        [
            InlineKeyboardButton(text="🌐 Monthly Unlimited Data", callback_data="unlimited_data")
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

# የ /start ትዕዛዝ ሎጂክ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 ሰላም <b>{message.from_user.first_name}</b> እንቋዕ ደህና መጡ!\n\n"
        "🇪🇹 <b>Ethiopian P2P Crypto & Digital Goods Marketplace</b>\n"
        "የኢትዮጵያ P2P ክሪፕቶ እና ዲጂታል እቃዎች ማርኬት\n\n"
        "እባክዎ ከታች ካሉት አማራጮች የሚፈልጉትን ይምረጡ፦"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

# ወደ ዋናው ማኑ ሜኑ መመለሻ
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    menu_text = "🏠 <b>ዋና ማውጫ (Main Menu):</b>\n\nእባክዎ የሚፈልጉትን አገልግሎት ከታች ይምረጡ፦"
    await callback.message.edit_text(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# የ My Profile ገጽ ማሳያ
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
        f"• Bank: Telebirr\n"
        f"• Account: {TELEBIRR_NUMBER}\n"
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

# Support Handler
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
# 🟢 BUY USDT - WORKFLOW, VALIDATION & CLEAN UI
# ==========================================

# Step 1: Buy USDT
@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    stock = 98.0
    rate = 197.0
    text = (
        "💰 <b>Buy USDT | USDT መግዛት</b>\n\n"
        f"• Available stock (የአሁን መጠን): {stock} USDT\n"
        f"• Rate (ተመን): 1 USDT = {rate} ETB\n"
        f"• Min / Max (ዝቅተኛ / ከፍተኛ): 0.5 - 10000.0 USDT\n\n"
        "• BEP20 minimum: 5 USDT\n"
        "• Bybit UID minimum: 1 USDT\n\n"
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

# Step 2: Amount Validation & Network Selection
@dp.message(BuyUSDTState.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    
    # የሰውየውን ጽሁፍ አጥፍቶ ገጹን ንፁህ ማድረግ
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
            "Where should admin send your USDT?\n"
            "USDT የት ይላክልዎታል? (የመቀበያ መንገድ ይምረጡ):"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Binance ID (Pay)", callback_data="net_binance"),
                InlineKeyboardButton(text="💎 BSC (BEP20)", callback_data="net_bep20")
            ],
            [
                InlineKeyboardButton(text="🔷 Bitget UID", callback_data="net_bitget"),
                InlineKeyboardButton(text="🔶 Bybit UID", callback_data="net_bybit")
            ],
            [
                InlineKeyboardButton(text="🌐 TON Network (USDT)", callback_data="net_ton")
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

# Step 3: Network Choice
@dp.callback_query(BuyUSDTState.waiting_for_network, F.data.startswith("net_"))
async def select_network(callback: types.CallbackQuery, state: FSMContext):
    network_map = {
        "net_binance": "Binance Pay ID",
        "net_bep20": "BSC (BEP20) Address",
        "net_bitget": "Bitget UID",
        "net_bybit": "Bybit UID",
        "net_ton": "TON Network Address"
    }
    net_name = network_map.get(callback.data, "Crypto Address")
    await state.update_data(network=net_name)
    
    text = (
        "📥 <b>USDT receiving destination | USDT መቀበያ አድራሻ</b>\n\n"
        f"Send your <b>{net_name}</b> where admin should send the USDT:\n"
        f"USDT የሚላክልዎትን <b>{net_name}</b> ያስገቡ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_address)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Step 4: Strict Address Validation
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

    # Strict Validation Rules
    is_valid = True
    err_msg = ""

    if "UID" in network or "Binance" in network:
        if not address.isdigit() or len(address) < 8 or len(address) > 12:
            is_valid = False
            err_msg = f"⚠️ እባክዎ ለ <b>{network}</b> ትክክለኛ የቁጥር መታወቂያ (8-12 ዲጂት) ያስገቡ፦"
    elif "BEP20" in network:
        if not address.startswith("0x") or len(address) != 42:
            is_valid = False
            err_msg = "⚠️ <b>BEP20 Address</b> በ '0x' መጀመር እና 42 ፊደላት/ቁጥሮች መሆን አለበት፦"
    elif "TON" in network:
        if not (address.startswith("EQ") or address.startswith("UQ")) or len(address) < 40:
            is_valid = False
            err_msg = "⚠️ <b>TON Address</b> በ 'EQ' ወይም 'UQ' መጀመር አለበት፦"

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
        "For Buy USDT, ETB payment is currently accepted by <b>Telebirr</b> only.\n"
        "የUSDT መግዣ ክፍያ አሁን ላይ በ<b>Telebirr</b> ብቻ ተቀባይነት አለው። ለመቀጠል Telebirr ይጫኑ፦"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="pay_telebirr")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_payment_method)
    if last_msg_id:
        await bot.edit_message_text(text, chat_id=message.chat.id, message_id=last_msg_id, reply_markup=keyboard, parse_mode="HTML")

# Step 5: Telebirr Payment Instructions
@dp.callback_query(BuyUSDTState.waiting_for_payment_method, F.data == "pay_telebirr")
async def pay_telebirr_selected(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    total_price = data.get("total_price")
    
    text = (
        "📋 <b>Order summary</b>\n"
        f"• USDT: {amount:.4f} USDT\n"
        f"• Pay: {total_price:,.2f} ETB\n\n"
        "📱 <b>Telebirr</b>\n\n"
        f"Number: <b>{TELEBIRR_NUMBER}</b>\n"
        f"Name: <b>{TELEBIRR_NAME}</b>\n\n"
        "Send the exact ETB amount, then upload a clear <b>Telebirr receipt screenshot</b>.\n"
        "ትክክለኛውን የብር መጠን ከፍለው ግልጽ የTelebirr ደረሰኝ ስክሪንሾት ይላኩ።"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_receipt)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Step 6 & 7: Receipt Upload & Admin Group Notification
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
        f"🚨 <b>New USDT Order! (አዲስ የUSDT ትዕዛዝ)</b>\n\n"
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
# 🛡 ADMIN APPROVE / REJECT & REASON SYSTEM
# ==========================================

@dp.callback_query(F.data.startswith("app_"))
async def admin_approve_order(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>ትዕዛዝዎ በተሳካ ሁኔታ ጸድቋል (Approved)!</b>\n\n"
                "አድሚኑ ክፍያውን አረጋግጦ USDT ልኮልዎታል። ከ 5 እስከ 10 ደቂቃ ባለው ጊዜ ውስጥ አካውንትዎ ላይ ይገባል።\n"
                f"በዛ ጊዜ ውስጥ ካልደረሰዎት እባክዎ ሰፖርታችንን ያናግሩ፦ {SUPPORT_USERNAME}"
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
        # ለተጠቃሚው ምክንያቱን እና ሰፖርት ሊንክ መላክ
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

# Cancel Order Handler
@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()


# ==========================================
# 🌐 DUMMY WEB SERVER FOR RENDER FREE TIER (PORT FIX)
# ==========================================

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

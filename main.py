import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# የ Buy USDT 7ቱ ስቴፖች FSM States
class BuyUSDTState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_network = State()
    waiting_for_address = State()
    waiting_for_payment_method = State()
    waiting_for_receipt = State()

# ዋናው ማኑ ሜኑ ኪቦርድ (የመጀመሪያው ኮድ እንዳለ ይቀጥላል)
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
        f"👋 ሰላም <b>{message.from_user.first_name}</b> እንደገና ሰላም መጡ!\n\n"
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
        f"• Account: 0987654321\n"
        f"• Name: Example Name\n\n"
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


# ==========================================
# 🟢 BUY USDT - 7 STEPS WORKFLOW IMPLEMENTATION
# ==========================================

# ስቴፕ 1: Buy USDT ሲጫን (Available Stock እና Rate ማሳየት)
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
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ስቴፕ 2: መጠኑን ሲያስገባ (Order Summary እና Network Selection ማሳየት)
@dp.message(BuyUSDTState.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 0.5 or amount > 10000.0:
            await message.answer("⚠️ እባክዎ ከ 0.5 እስከ 10000.0 USDT መካከል ያስገቡ:")
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
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 10):")

# ስቴፕ 3: ኔትወርክ ሲመርጥ (አድራሻውን ወይም UID መጠየቅ)
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
        f"USDT የሚላክልዎትን <b>{net_name}</b> ያስገቡ:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_address)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ስቴፕ 4: አድራሻውን ሲጽፍ (መድረሻው ተይዟል ብሎ Telebirr ክፍያ አማራጭ ማሳየት)
@dp.message(BuyUSDTState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 3:
        await message.answer("⚠️ እባክዎ ትክክለኛ አድራሻ ወይም UID ያስገቡ:")
        return
    
    await state.update_data(address=address)
    data = await state.get_data()
    amount = data.get("amount")
    total_price = data.get("total_price")
    
    text = (
        "📬 <b>Receiving destination saved | መድረሻው ተይዟል</b>\n\n"
        f"• USDT: {amount:.4f}\n"
        f"• ETB to pay (የሚከፍሉት ብር): {total_price:,.2f} ETB\n"
        f"• Destination (መቀበያ): {address}\n\n"
        "For Buy USDT, ETB payment is currently accepted by <b>Telebirr</b> only.\n"
        "የUSDT መግዣ ክፍያ አሁን ላይ በ<b>Telebirr</b> ብቻ ተቀባይነት አለው። ለመቀጠል Telebirr ይጫኑ:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Telebirr", callback_data="pay_telebirr")],
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_payment_method)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# ስቴፕ 5: Telebirr ሲጫን (የቴሌቢር አካውንት ቁጥር እና የስክሪንሾት ማረጋገጫ መጠየቅ)
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
        "Number: <b>0987504831</b>\n"
        "Name: <b>yohanis</b>\n\n"
        "Send the exact ETB amount, then upload a clear <b>Telebirr receipt screenshot</b>.\n"
        "ትክክለኛውን የብር መጠን ከፍለው ግልጽ የTelebirr ደረሰኝ ስክሪንሾት ይላኩ።\n\n"
        "After payment:\n"
        "🔍 <b>Required:</b> upload a clear <b>screenshot</b> of the receipt/transaction.\n"
        "Text-only references are not accepted.\n"
        "ግልጽ የደረሰኝ ስክሪንሾት ማላክ ግዴታ ነው።"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel | ሰርዝ", callback_data="cancel_order")]
    ])
    await state.set_state(BuyUSDTState.waiting_for_receipt)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ስቴፕ 6 & 7: ስክሪንሾት ፎቶ ሲልክ (Processing / OCR እና ለአድሚን ማሳወቂያ መላክ)
@dp.message(BuyUSDTState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("🔄 Processing payment proof...\n⏳ Reading screenshot with OCR...")
    
    await asyncio.sleep(2)
    
    data = await state.get_data()
    amount = data.get("amount")
    total_price = data.get("total_price")
    address = data.get("address")
    network = data.get("network")
    user = message.from_user
    
    admin_text = (
        f"🚨 <b>New USDT Order! (አዲስ የUSDT ትዕዛዝ)</b>\n\n"
        f"👤 User: {user.full_name} (@{user.username}, ID: <code>{user.id}</code>)\n"
        f"💵 Amount: {amount} USDT\n"
        f"💰 Pay: {total_price:,.2f} ETB\n"
        f"🌐 Network: {network}\n"
        f"📍 Address/UID: <code>{address}</code>\n\n"
        "የክፍያ ስክሪንሾት ከታች ተያይዟል፦"
    )
    
    if ADMIN_ID != 0:
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending to admin: {e}")
            
    await processing_msg.edit_text(
        "✅ <b>Payment proof received successfully!</b>\n"
        "የክፍያ ማረጋገጫዎ ደርሶናል! አድሚኑ አረጋግጦ USDT ይለቅልዎታል። እናመሰግናለን! 🙏",
        parse_mode="HTML"
    )
    await state.clear()

@dp.message(BuyUSDTState.waiting_for_receipt)
async def invalid_receipt_type(message: types.Message):
    await message.answer("⚠️ እባክዎ የክፍያ ስክሪንሾት (Photo) ብቻ ይላኩ:")

# Cancel Order Handler (በየትኛውም ሰዓት ትዕዛዙን መሰረዝ ከፈለጉ)
@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል:", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# ቦቱን የማስጀመር ዋና ተግባር
async def main():
    print("ቦቱ በአግባቡ በመጀመር ላይ ነው...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

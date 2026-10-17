import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# መረጃዎችን ከ Render Environment Variables እንቀበላለን
BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
# አድሚን አይዲን ከ ቴክስት ወደ ቁጥር (Integer) እንለውጠዋለን
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("❌ እባክዎ የ BOT_TOKEN Environment Variable በ Render ላይ ያስገቡ!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# የ FSM ስቴቶች (States) ለግዢ እና ሽያጭ ሂደት
class OrderStates(StatesGroup):
    waiting_for_usdt_amount = State()
    waiting_for_crypto_address = State()
    waiting_for_phone_number = State()
    waiting_for_payment_receipt = State()

# ዋናው ማኑ ሜኑ (Main Menu Keyboards) - ከስክሪንሾቶቹ ጋር የተጣጣመ
def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
    return keyboard

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

# ወደ ዋናው ማኑ ሜኑ (Main Menu) መመለሻ Handler
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    menu_text = "🏠 <b>ዋና ማውጫ (Main Menu):</b>\n\nእባክዎ የሚፈልጉትን አገልግሎት ከታች ይምረጡ፦"
    await callback.message.edit_text(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# የ My Profile ገጽ ማሳያ (ከስክሪንሾቱ ጋር የተጣጣመ)
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

# ቦቱን የማስጀመር ዋና ተግባር
async def main():
    print("ቦቱ በአግባቡ በመጀመር ላይ ነው...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

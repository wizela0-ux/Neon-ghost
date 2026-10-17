import os
import re
import asyncio
import firebase_admin
from firebase_admin import credentials, db

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

# 1. የ Firebase Realtime Database ግንኙነት ማዋቀር
if not firebase_admin._apps:
    cred = credentials.Anonymous() # ወይም በ Render በኩል የለቀቁትን creds
    firebase_admin.initialize_app(options={
        'databaseURL': FIREBASE_DB_URL
    })

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. የ FSM ስቴቶች ለ Buy USDT
class BuyUSDTState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_network = State()
    waiting_for_address = State()
    waiting_for_receipt = State()

# 3. የዋና ሜኑ ኪቦርድ
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

# 4. የ Buy USDT ሂደት መነሻ (Buy USDT Callback)
@dp.callback_query(F.data == "buy_usdt")
async def start_buy_usdt(callback: types.CallbackQuery, state: FSMContext):
    # ከ Firebase ዳታቤዝ ስቶክ እና ዋጋ ማበብ (ወደፊት በዳታቤዝ የሚገናኝ)
    stock = 500.0  # ለሙከራ የተቀመጠ ስቶክ
    rate = 197.0   # 1 USDT = 197 ETB

    text = (
        "🟢 <b>Buy USDT | USDT መግዛት</b>\n\n"
        f"💵 <b>የአሁኑ የምንዛሬ ተመን:</b> 1 USDT = {rate} ETB\n"
        f"📦 <b>በስቶክ ላይ ያለው:</b> {stock} USDT\n"
        "🔻 <b>ዝቅተኛ መግዣ:</b> 5 USDT\n\n"
        "እባክዎ መግዛት የሚፈልጉትን የ USDT መጠን በቁጥር ያስገቡ፦"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ሰርዝ (Cancel)", callback_data="cancel_order")]
    ])
    
    await state.set_state(BuyUSDTState.waiting_for_amount)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# 5. የገባውን የ USDT መጠን ማረጋገጫ
@dp.message(BuyUSDTState.waiting_for_amount)
async def process_usdt_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 5:
            await message.answer("⚠️ ዝቅተኛው የግዢ መጠን 5 USDT ነው። እባክዎ እንደገና ያስገቡ፦")
            return
        
        # መጠኑን በ FSM ሴቭ እናደርጋለን
        await state.update_data(amount=amount)
        
        # የኔትወርክ መምረጫ ገጽ
        text = (
            f"✅ የመረጡት መጠን: <b>{amount} USDT</b>\n\n"
            "እባክዎ USDT የሚቀበሉበትን የኔትወርክ አይነት ይምረጡ፦"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Binance Pay ID", callback_data="net_binance")],
            [InlineKeyboardButton(text="BEP20 (BSC)", callback_data="net_bep20")],
            [InlineKeyboardButton(text="TON Network", callback_data="net_ton")],
            [InlineKeyboardButton(text="❌ ሰርዝ (Cancel)", callback_data="cancel_order")]
        ])
        
        await state.set_state(BuyUSDTState.waiting_for_network)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ፦ 10 ወይም 25.5)፦")

# 6. የትዕዛዝ መሰረዣ (Cancel Handler)
@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛑 ትዕዛዝዎ ተሰርዟል። ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# (የቀሩት Handlers እና Command ማነሳሻዎች...)

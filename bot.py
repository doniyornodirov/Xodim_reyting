import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- TOKEN VA GURUH SOZLAMALARI ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENINGIZNI_SHU_YERGA_YOZING")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "-100XXXXXXXXXX")  # Arizalar boradigan guruh ID-si

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()

# CORS sozlamalari (Mini App xatosiz ulanishi uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vaqtinchalik xotira (Baza vazifasini bajaradi)
HISTORY_DATA = []


# ==========================================
# 1. TELEGRAM BOT FUNKSIYALARI (BUYRUQLARI)
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Botga /start bosilganda ishlaydigan asosiy funksiya"""
    user_name = message.from_user.first_name
    await message.answer(
        f"Assalomu alaykum, {user_name}!\n\n"
        f"Ushbu bot orqali xodimlar hisobot va arizalarini yuborishlari mumkin. "
        f"Iltimos, Mini App (veb-sahifa) orqali ma'lumotlarni yuboring."
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam buyrug'i"""
    await message.answer(
        "🛠 **Yordam menyusi:**\n\n"
        "• Ariza yuborish uchun Mini App'ga kiring.\n"
        "• Kiritilgan summa avtomatik ravishda +3% qo'shilib guruhga yuboriladi.\n"
        "• Rahbarlar guruhdagi tugmalar orqali arizani tasdiqlashi yoki rad etishi mumkin."
    )


# ==========================================
# 2. FASTAPI SERVER VA API ENDPOINT'LARI
# ==========================================

class SendRequest(BaseModel):
    card_number: str
    name: str
    amount: str

@app.post("/api/send")
async def send_to_group(data: SendRequest):
    """Mini App'dan kelgan ma'lumotni qabul qilib, guruhga yuborish"""
    try:
        amount_num = float(data.amount)
        total_amount = amount_num * 1.03  # +3% qo'shish
        
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M")
        
        req_id = len(HISTORY_DATA) + 1
        
        item = {
            "id": req_id,
            "card_number": data.card_number,
            "name": data.name,
            "amount": f"{amount_num:,.0f}".replace(",", " "),
            "total_amount": f"{total_amount:,.0f}".replace(",", " "),
            "date": date_str,
            "time": time_str,
            "status": "pending"  # Boshlang'ich holat: Kutilmoqda
        }
        HISTORY_DATA.insert(0, item)
        
        # Guruhga yuboriladigan xabar matni
        text = (
            f"📥 <b>Yangi ariza! (#ID{req_id})</b>\n\n"
            f"💳 <b>Karta:</b> <code>{data.card_number}</code>\n"
            f"👤 <b>F.I.O:</b> {data.name}\n"
            f"💰 <b>Asl summa:</b> {amount_num:,.0f} so'm ➔ <b>+3%:</b> {total_amount:,.0f} so'm"
        )
        
        # Guruhdagi adminlar uchun tasdiqlash/rad etish tugmalari
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{req_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{req_id}")
            ]
        ])
        
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=text, parse_mode="HTML", reply_markup=keyboard)
        return {"status": "ok", "id": req_id}
    except Exception as e:
        print(f"Xatolik: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history():
    """Mini App uchun tarix ma'lumotlarini qaytarish"""
    return HISTORY_DATA


# ==========================================
# 3. GURUHDAGI TUGMALARNI BOSHQARISH (CALLBACK)
# ==========================================

@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def process_status_change(callback: CallbackQuery):
    """Admin guruhda tasdiqlash yoki rad etish tugmasini bosganda ishlaydi"""
    action, req_id_str = callback.data.split("_")
    req_id = int(req_id_str)
    
    target_item = next((item for item in HISTORY_DATA if item["id"] == req_id), None)
    
    if target_item:
        if action == "approve":
            target_item["status"] = "approved"
            status_text = "<b>Tasdiqlandi ✅</b>"
        else:
            target_item["status"] = "rejected"
            status_text = "<b>Rad etildi ❌</b>"
        
        # Guruhdagi xabarni yangilash (tugmalarni olib tashlab, statusni yozib qo'yish)
        original_text = callback.message.html_text
        updated_text = f"{original_text}\n\nStatus: {status_text}"
        
        await callback.message.edit_text(text=updated_text, parse_mode="HTML", reply_markup=None)
        await callback.answer(f"Ariza muvaffaqiyatli o'zgartirildi!")
    else:
        await callback.answer("Ariza topilmadi!", show_alert=True)


# ==========================================
# 4. STATIK FAYL VA BOTNI ISHGA TUSHIRISH
# ==========================================

@app.get("/")
async def read_index():
    """Mini App ochiladigan asosiy HTML sahifani ulash"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "index.html topilmadi"}

@app.on_event("startup")
async def on_startup():
    """FastAPI ishga tushishi bilan Telegram botni fon rejimida (polling) yoqish"""
    asyncio.create_task(dp.start_polling(bot))

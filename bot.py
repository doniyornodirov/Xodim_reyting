import asyncio
import json
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo,
)

TOKEN = "8772920592:AAGOhO9FJTXP4JU2YyufyaJOiY2IvANWttQ"
GROUP_ID = -1003747381544
ADMIN_ID = 8686341550

WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/"
GIVEN_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/berilgan.html"
ADMIN_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/admin.html"
HISTORY_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/tarix.html"
MY_HISTORY_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/my_tarix.html"
REPORT_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/hisobot.html"
DEBT_WEB_APP_URL = "https://doniyornodirov.github.io/Xodim_reyting/qarzdorlik.html"

bot = Bot(token=TOKEN)
router = Router()

def init_db():
    conn = sqlite3.connect("reports.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            employee_name TEXT,
            card_holder TEXT,
            card_number TEXT,
            amount REAL,
            final_amount REAL,
            status TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS given_amounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            employee_name TEXT,
            amount REAL,
            comment TEXT,
            status TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_employees (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE allowed_employees ADD COLUMN debt REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # 30 kundan eski yozuvlarni tozalash
    cursor.execute("""
        DELETE FROM transactions 
        WHERE status != 'Kutilmoqda' 
        AND date < DATETIME('now', '-30 days')
    """)
    
    conn.commit()
    conn.close()

init_db()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    profile_name = message.from_user.full_name or "Xodim"
    
    if user_id == ADMIN_ID:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👥 Xodimlar ro'yxati va boshqarish", web_app=WebAppInfo(url=ADMIN_WEB_APP_URL))],
                [KeyboardButton(text="💸 Xodimlar qarzdorligini belgilash", web_app=WebAppInfo(url=DEBT_WEB_APP_URL))],
                [KeyboardButton(text="📋 Olingan summalar tarixi", web_app=WebAppInfo(url=HISTORY_WEB_APP_URL))]
            ],
            resize_keyboard=True
        )
        await message.answer("Assalomu alaykum Rahbar!\n\nPanelni ochish uchun pastdagi tugmani bosing:", reply_markup=keyboard)
        return

    conn = sqlite3.connect("reports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM allowed_employees WHERE user_id = ?", (user_id,))
    employee = cursor.fetchone()

    if employee:
        current_name = employee[0]
        if not current_name or "Xodim #" in current_name or current_name == "Xodim":
            cursor.execute("UPDATE allowed_employees SET full_name = ? WHERE user_id = ?", (profile_name, user_id))
            conn.commit()
            current_name = profile_name
            
        cursor.execute("SELECT debt FROM allowed_employees WHERE user_id = ?", (user_id,))
        debt_row = cursor.fetchone()
        emp_debt = debt_row[0] if (debt_row and debt_row[0] is not None) else 0

        cursor.execute("SELECT SUM(amount) FROM given_amounts WHERE user_id = ? AND status = 'Tasdiqlandi'", (user_id,))
        given_row = cursor.fetchone()
        emp_given = given_row[0] if (given_row and given_row[0] is not None) else 0

        cursor.execute("SELECT SUM(final_amount) FROM transactions WHERE user_id = ? AND status = 'Tasdiqlandi'", (user_id,))
        card_row = cursor.fetchone()
        emp_card = card_row[0] if (card_row and card_row[0] is not None) else 0

        conn.close()

        custom_report_url = f"{REPORT_WEB_APP_URL}?debt={emp_debt}&given={emp_given}&card={emp_card}"

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Karta to'ldirish formasini ochish", web_app=WebAppInfo(url=WEB_APP_URL))],
                [KeyboardButton(text="📊 Kunlik hisobot topshirish", web_app=WebAppInfo(url=custom_report_url))],
                [KeyboardButton(text="📜 Berilgan summalar tarixi", web_app=WebAppInfo(url=MY_HISTORY_WEB_APP_URL))]
            ],
            resize_keyboard=True
        )
        await message.answer(f"Assalomu alaykum, {current_name}! Kerakli bo'limni tanlang:", reply_markup=keyboard)
    else:
        conn.close()
        await message.answer(
            f"Assalomu alaykum! Siz tizimda ro'yxatdan o'tmagansiz.\n\n"
            f"Sizning Telegram ID raqamingiz: <code>{user_id}</code>\n\n"
            "Iltimos, ushbu ID raqamingizni rahbarga yuboring.",
            parse_mode="HTML"
        )

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id

        conn = sqlite3.connect("reports.db")
        cursor = conn.cursor()

        if data.get("action") == "update_debt":
            if user_id == ADMIN_ID:
                target_user_id = int(data["user_id"])
                added_debt = float(data["debt"])
                
                cursor.execute("SELECT full_name, debt FROM allowed_employees WHERE user_id = ?", (target_user_id,))
                emp = cursor.fetchone()
                
                if emp:
                    current_debt = emp[1] if emp[1] is not None else 0
                    total_debt = current_debt + added_debt
                    
                    cursor.execute("UPDATE allowed_employees SET debt = ? WHERE user_id = ?", (total_debt, target_user_id))
                    conn.commit()
                    await message.answer(f"✅ <b>{emp[0]}</b> ning qarzdorligiga <b>{added_debt:,.0f} so'm</b> qo'shildi.\nJami qarz: <b>{total_debt:,.0f} so'm</b>", parse_mode="HTML")
                else:
                    cursor.execute("INSERT INTO allowed_employees (user_id, full_name, debt) VALUES (?, ?, ?)", (target_user_id, f"Xodim #{target_user_id}", added_debt))
                    conn.commit()
                    await message.answer(f"✅ Yangi xodim (ID: {target_user_id}) bazaga qo'shildi va qarzdorligi <b>{added_debt:,.0f} so'm</b> etib belgilandi.", parse_mode="HTML")
            conn.close()
            return

        cursor.execute("SELECT full_name FROM allowed_employees WHERE user_id = ?", (user_id,))
        emp_row = cursor.fetchone()
        if emp_row and emp_row[0] and "Xodim #" not in emp_row[0]:
            employee_name = emp_row[0]
        else:
            employee_name = message.from_user.full_name or f"Xodim #{user_id}"

        # Karta to'ldirish so'rovi
        if data.get("type") == "card_transaction" or "card_number" in data:
            card_number = data.get("card_number")
            card_holder = data.get("card_holder")
            amount = float(data.get("amount", 0))
            final_amount = amount * 1.03

            cursor.execute(
                "INSERT INTO transactions (user_id, employee_name, card_holder, card_number, amount, final_amount, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, employee_name, card_holder, card_number, amount, final_amount, "Kutilmoqda")
            )
            tx_id = cursor.lastrowid
            conn.commit()
            conn.close()

            text = (
                f"<b>💳 Karta to'ldirish so'rovi #{tx_id}</b>\n\n"
                f"👤 Xodim: <b>{employee_name}</b>\n"
                f"🔢 Karta: <code>{card_number}</code>\n"
                f"👤 Egasi: {card_holder}\n"
                f"💰 Asl summa: {amount:,.2f} so'm\n"
                f"📈 +3% bilan: <b>{final_amount:,.2f} so'm</b>\n"
                f"📌 <b>Status: ⏳ Kutilmoqda</b>"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash (+3%)", callback_data=f"card_accept_{tx_id}"),
                        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"card_reject_{tx_id}")
                    ]
                ]
            )

            await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode="HTML", reply_markup=keyboard)
            await message.answer("✅ Karta to'ldirish so'rovi guruhga yuborildi!")
            return

        conn.close()
    except Exception as e:
        print(f"Xatolik: {e}")

@router.callback_query(F.data.startswith("card_"))
async def process_card_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Bu amalni faqat rahbar bajarishi mumkin!", show_alert=True)
        return

    data_parts = callback.data.split("_")
    action = data_parts[1]
    tx_id = int(data_parts[2])

    conn = sqlite3.connect("reports.db")
    cursor = conn.cursor()

    status_text = "✅ Tasdiqlandi" if action == "accept" else "❌ Rad etildi"
    new_status = "Tasdiqlandi" if action == "accept" else "Rad etildi"

    cursor.execute("UPDATE transactions SET status = ? WHERE id = ?", (new_status, tx_id))
    cursor.execute("SELECT user_id, amount, final_amount, card_number, card_holder, employee_name FROM transactions WHERE id = ?", (tx_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()

    if res:
        emp_user_id, amount, final_amount, card_number, card_holder, employee_name = res
        
        updated_text = (
            f"<b>💳 Karta to'ldirish so'rovi #{tx_id}</b>\n\n"
            f"👤 Xodim: <b>{employee_name}</b>\n"
            f"🔢 Karta: <code>{card_number}</code>\n"
            f"👤 Egasi: {card_holder}\n"
            f"💰 Asl summa: {amount:,.2f} so'm\n"
            f"📈 +3% bilan: <b>{final_amount:,.2f} so'm</b>\n"
            f"📌 <b>Status: {status_text}</b>"
        )
        
        try:
            await callback.message.edit_text(updated_text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass

    await callback.answer(f"So'rov {new_status.lower()}!")

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot ishga tushdi va xabarlarni kutmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
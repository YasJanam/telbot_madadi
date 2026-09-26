import asyncio
import base64
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

from baleio import Bot, Dispatcher
from baleio.types import Message
from baleio.filters import Command
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from sheets import add_or_update_user, mark_day_sent_in_sheet


# ---------- تنظیمات ----------
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = "users_bale.db"


# ---------- گوگل شیت ----------
SHEET_ID = os.getenv("SHEET_ID")
WORKSHEET_NAME = "Users"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ---------- محتوای هدیه و سناریو ----------
GIFT_LINK = "https://ziresefr.com/"

DAY_1_MESSAGE = (
    "🎬 روز اول!\n\n"
    "این اولین فیلم آموزشی برای شماست:\n"
    "https://example.com/video-day-1"
)
DAY_2_MESSAGE = (
    "🎬 روز دوم!\n\n"
    "فیلم دوم آماده‌ست:\n"
    "https://example.com/video-day-2"
)
DAY_3_MESSAGE = (
    "🎁 روز سوم!\n\n"
    "تبریک! به پایان سناریو رسیدی. این هم هدیه‌ی نهایی:\n"
    "https://example.com/final-bonus"
)


# ---------- دیتابیس ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            day1_sent INTEGER DEFAULT 0,
            day2_sent INTEGER DEFAULT 0,
            day3_sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_user(bale_id, username, full_name, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, full_name, phone, day1_sent, day2_sent, day3_sent)
        VALUES (?, ?, ?, ?, 0, 0, 0)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            phone = excluded.phone,
            day1_sent = 0,
            day2_sent = 0,
            day3_sent = 0
    """, (bale_id, username, full_name, phone))
    conn.commit()
    conn.close()
    logger.info(f"💾 کاربر {bale_id} در SQLite ذخیره شد")

    # گوگل شیت
    try:
        add_or_update_user(bale_id, username, full_name, phone)
    except Exception as e:
        logger.warning(f"⚠️ خطای شیت (SQLite اوکی): {e}")



def mark_day_sent(bale_id, day):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET day{day}_sent = 1 WHERE telegram_id = ?",
        (bale_id,),
    )
    conn.commit()
    conn.close()


def user_exists(bale_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (bale_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_users_for_restore():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT telegram_id, joined_at, day1_sent, day2_sent, day3_sent
        FROM users
        WHERE day1_sent = 0 OR day2_sent = 0 OR day3_sent = 0
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows




# ---------- زمان‌بندی سناریو ----------
DAY_1_DELAY = timedelta(seconds=1)
DAY_2_DELAY = timedelta(seconds=5)
DAY_3_DELAY = timedelta(seconds=10)


async def schedule_scenario(bot, bale_id, joined_at=None):
    if joined_at is None:
        joined_at = datetime.now()

    delays = {1: DAY_1_DELAY, 2: DAY_2_DELAY, 3: DAY_3_DELAY}

    for day, delay in delays.items():
        target_time = joined_at + delay
        seconds_until = (target_time - datetime.now()).total_seconds()
        if seconds_until < 1:
            seconds_until = 1

        asyncio.create_task(
            send_delayed_message(bot, bale_id, day, seconds_until)
        )
        logger.info(f"⏰ روز {day} برای {bale_id} → {seconds_until:.0f} ثانیه دیگه")


async def send_delayed_message(bot, bale_id, day, seconds):
    await asyncio.sleep(seconds)

    messages = {1: DAY_1_MESSAGE, 2: DAY_2_MESSAGE, 3: DAY_3_MESSAGE}
    message = messages[day]

    try:
        await bot.send_message(chat_id=bale_id, text=message)
        mark_day_sent(bale_id, day)
        mark_day_sent_in_sheet(bale_id, day)
        logger.info(f"✅ پیام روز {day} برای {bale_id} ارسال شد")
    except Exception as e:
        logger.exception(f"❌ خطا در ارسال روز {day}: {e}")


# ---------- ربات و دیسپچر ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# وضعیت کاربران
user_states = {}
user_data = {}
FULL_NAME, PHONE = range(2)


# ---------- هندلرها ----------
@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"🟢 START برای {user_id}")

   
    if user_exists(user_id):
        await message.answer(
            "قبلاً ثبت‌نام کردی.\n"
            "اگه می‌خوای از نو، /restart بزن."
        )
        return

    user_states[user_id] = FULL_NAME
    user_data[user_id] = {}

    await message.answer(
        f"سلام {message.from_user.first_name} 👋\n\n"
        "به ربات ما خوش آمدی!\n"
        "برای شروع، **اسم و فامیل کاملت** رو بفرست.\n\n"
        "برای انصراف /cancel"
    )


@dp.message(Command("cancel"))
async def cancel_handler(message: Message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    user_data.pop(user_id, None)
    await message.answer("لغو شد. هر وقت خواستی /start بزن.")


@dp.message(Command("restart"))
async def restart_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"🔵 RESTART برای {user_id}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))
    conn.commit()
    conn.close()

    user_states.pop(user_id, None)
    user_data.pop(user_id, None)

    await message.answer("🗑 اطلاعاتت پاک شد.\nبرای شروع مجدد /start رو بزن.")


@dp.message()
async def message_handler(message: Message):
    """فقط پیام‌های غیردستوری اینجا میان"""
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    if not text:
        return

    state = user_states.get(user_id)

    # ----- مرحله ۱: گرفتن اسم -----
    if state == FULL_NAME:
        user_data[user_id]["full_name"] = text
        user_states[user_id] = PHONE

        await message.answer(
            "ممنون! حالا **شماره تلفنت** رو بفرست.\n"
            "مثلاً: 09123456789"
        )
        return

    # ----- مرحله ۲: گرفتن شماره -----
    if state == PHONE:
        phone = text
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) < 10:
            await message.answer("❌ شماره معتبر نیست. دوباره بفرست.")
            return

        full_name = user_data[user_id]["full_name"]
        username = message.from_user.username or ""

        save_user(user_id, username, full_name, phone)

        await message.answer(
            "✅ ثبت‌نامت با موفقیت انجام شد!\n\n"
            f"👤 نام: {full_name}\n"
            f"📞 شماره: {phone}\n\n"
            "🎁 این هم هدیه‌ی خوش‌آمدگویی:\n"
            f"{GIFT_LINK}\n\n"
            "📅 از الان، به مدت ۳ روز، هر روز یه محتوای ویژه برات می‌فرستیم. منتظر باش!"
        )

        await schedule_scenario(bot, user_id, datetime.now())

        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    # ----- کاربر توی مکالمه نیست -----
    if user_exists(user_id):
        await message.answer("قبلاً ثبت‌نام کردی. /restart بزن اگه می‌خوای از نو.")
    else:
        await message.answer("برای شروع /start بزن.")


# ---------- بازیابی بعد از ری‌استارت ----------
async def restore_scheduled_jobs():
    users = get_users_for_restore()
    logger.info(f"♻️ {len(users)} کاربر برای بازیابی پیدا شد")

    for bale_id, joined_at, d1, d2, d3 in users:
        if d1 and d2 and d3:
            continue

        try:
            joined_at_dt = datetime.strptime(joined_at, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            joined_at_dt = datetime.now()

        delays = {1: DAY_1_DELAY, 2: DAY_2_DELAY, 3: DAY_3_DELAY}
        sent_flags = {1: d1, 2: d2, 3: d3}

        for day, delay in delays.items():
            if sent_flags[day]:
                continue
            target = joined_at_dt + delay
            secs = (target - datetime.now()).total_seconds()
            if secs < 1:
                secs = 1

            asyncio.create_task(send_delayed_message(bot, bale_id, day, secs))
            logger.info(f"♻️ بازیابی روز {day} برای {bale_id}")


# ---------- main ----------
async def main():
    init_db()
    await restore_scheduled_jobs()

    logger.info("🤖 ربات بله در حال اجراست...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from sheets import add_or_update_user

import os
from dotenv import load_dotenv


load_dotenv()

# ---------- تنظیمات ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

#BOT_TOKEN = "7993611032:AAHvO3lXyLC44RUW32TrZuaclZBsfmglazM"  
BOT_TOKEN = os.getenv("BOT_TOKEN")

DB_NAME = "users_telbot.db"

#gs = gspread.service_account(filename="telegram-bot-madadi-1-c01d2cec4eb5.json")
#SHEET_ID = "1AGU9oEj2xMN6Fb0x2wrgMoqICkeDKlnu0UvdXExAN4g"

# ---------- محتوای هدیه و سناریو ----------
GIFT_LINK = "https://ziresefr.com/"  

DAY_1_MESSAGE = (
    "🎬 روز اول!\n\n"
    "این اولین فیلم آموزشی برای شماست:\n"
    "https://ziresefr.org/product/challenge-of-achieving-goals/"
)

DAY_2_MESSAGE = (
    "🎬 روز دوم!\n\n"
    "فیلم دوم آماده‌ست:\n"
    "https://ziresefr.org/product/free-overcome-procrastination/"
)

DAY_3_MESSAGE = (
    "🎁 روز سوم!\n\n"
    "تبریک! این هم هدیه‌ی نهایی:\n"
    "https://ziresefr.org/courses/sshuman/"
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


def save_user(telegram_id, username, full_name, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, full_name, phone)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            phone = excluded.phone
    """, (telegram_id, username, full_name, phone))
    conn.commit()
    conn.close()

    try:
        add_or_update_user(telegram_id, username, full_name, phone)
    except Exception as e:
        print(f"⚠️ ذخیره در شیت موفق نبود (ولی SQLite اوکی): {e}")
    


def mark_day_sent(telegram_id, day):
    """ثبت این‌که پیام فلان روز ارسال شده"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET day{day}_sent = 1 WHERE telegram_id = ?",
        (telegram_id,),
    )
    conn.commit()
    conn.close()


def get_users_for_restore():
    """کاربرانی که هنوز همه‌ی پیام‌هاشون ارسال نشده (برای بازیابی بعد از ری‌استارت)"""
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



def schedule_scenario(app, telegram_id, joined_at=None):
    """زمان‌بندی سه پیام برای کاربر"""
    print(f"🟣 SCHEDULE صدا زده شد برای {telegram_id}")

    if app is None:
        print("🟣❌ app برابر None است!")
        return

    if app.job_queue is None:
        print("🟣❌ JobQueue فعال نیست!")
        return

    if joined_at is None:
        joined_at = datetime.now()
    elif isinstance(joined_at, str):
        try:
            joined_at = datetime.strptime(joined_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            joined_at = datetime.now()

    # پاک کردن jobهای قبلی این کاربر
    for day in (1, 2, 3):
        for job in app.job_queue.get_jobs_by_name(f"day{day}_{telegram_id}"):
            job.schedule_removal()
            #print(f"🟣 job قدیمی day{day}_{telegram_id} حذف شد")

    now = datetime.now()
    delays = {1: DAY_1_DELAY, 2: DAY_2_DELAY, 3: DAY_3_DELAY}

    for day, delay in delays.items():
        target_time = joined_at + delay
        seconds_until = (target_time - now).total_seconds()
        if seconds_until < 1:
            seconds_until = 1

        app.job_queue.run_once(
            callback=send_day_message,
            when=seconds_until,
            data={"telegram_id": telegram_id, "day": day},
            name=f"day{day}_{telegram_id}",
        )
        print(f"🟣✅ روز {day} ثبت شد، {seconds_until:.0f} ثانیه دیگه")
        logger.info(f"⏰ روز {day} برای {telegram_id} → {seconds_until:.0f} ثانیه دیگه")



async def send_day_message(context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام هر روز"""
    data = context.job.data
    telegram_id = data["telegram_id"]
    day = data["day"]

    messages = {1: DAY_1_MESSAGE, 2: DAY_2_MESSAGE, 3: DAY_3_MESSAGE}
    message = messages[day]

    try:
        await context.bot.send_message(chat_id=telegram_id, text=message)
        mark_day_sent(telegram_id, day)
        logger.info(f"✅ پیام روز {day} برای {telegram_id} ارسال شد")
    except Exception as e:
        logger.exception(f"❌ خطا در ارسال پیام روز {day} برای {telegram_id}: {e}")


# ---------- مراحل گفتگو ----------
FULL_NAME, PHONE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM users WHERE telegram_id = ?", (user.id,))
    existing = cursor.fetchone()
    conn.close()

    if existing:
        await update.message.reply_text(
            f"سلام {existing[0]} 👋\n"
            "قبلاً ثبت‌نام کردی. سناریوت در جریانه.\n"
            "اگر می‌خوای دوباره ثبت‌نام کنی، /restart رو بزن."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"سلام {user.first_name} 👋\n\n"
        "به ربات ما خوش آمدی!\n"
        "برای شروع، **اسم و فامیل کاملت** رو بفرست.\n\n"
        "برای انصراف /cancel",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return FULL_NAME


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text.strip()

    contact_keyboard = ReplyKeyboardMarkup(
        [[{"text": "📱 ارسال شماره من", "request_contact": True}]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "ممنون! حالا **شماره تلفنت** رو بفرست.\n"
        "می‌تونی روی دکمه‌ی زیر بزنی یا دستی تایپ کنی.",
        parse_mode="Markdown",
        reply_markup=contact_keyboard,
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    digits = "".join(filter(str.isdigit, phone))
    if len(digits) < 10:
        await message.reply_text("❌ شماره معتبر نیست. دوباره بفرست.")
        return PHONE

    user = update.effective_user
    full_name = context.user_data["full_name"]

    # ذخیره در دیتابیس
    save_user(user.id, user.username, full_name, phone)

    # ارسال هدیه
    await message.reply_text(
        "✅ ثبت‌نامت با موفقیت انجام شد!\n\n"
        f"👤 نام: {full_name}\n"
        f"📞 شماره: {phone}\n\n"
        "📅 از امروز، به مدت ۳ روز، هر روز یه محتوای ویژه 🎁 برات می‌فرستیم. منتظر باش!",
        reply_markup=ReplyKeyboardRemove(),
    )

    # زمان‌بندی سناریو
    schedule_scenario(context.application, user.id, datetime.now())

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو مکالمه - چه داخل مکالمه، چه بیرون"""
    context.user_data.clear()

    await update.message.reply_text(
        "لغو شد. هر وقت خواستی /start بزن.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن اطلاعات قبلی + حذف jobها + هدایت به /start"""
    user = update.effective_user

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (user.id,))
    conn.commit()
    conn.close()

    for day in (1, 2, 3):
        jobs = context.application.job_queue.get_jobs_by_name(f"day{day}_{user.id}")
        for job in jobs:
            job.schedule_removal()

    context.user_data.clear()

    await update.message.reply_text(
        "🗑 اطلاعاتت پاک شد.\n"
        "برای شروع مجدد /start رو بزن.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def restore_scheduled_jobs(app: Application):
    """اگه ربات ری‌استارت شد، job های باقی‌مونده رو دوباره بساز"""
    users = get_users_for_restore()
    for telegram_id, joined_at, d1, d2, d3 in users:
        if d1 and d2 and d3:
            continue

        joined_at_dt = datetime.strptime(joined_at, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        delays = {1: DAY_1_DELAY, 2: DAY_2_DELAY, 3: DAY_3_DELAY}
        sent_flags = {1: d1, 2: d2, 3: d3}

        for day, delay in delays.items():
            if sent_flags[day]:
                continue
            target = joined_at_dt + delay
            secs = (target - now).total_seconds()
            if secs < 1:
                secs = 1

            app.job_queue.run_once(
                callback=send_day_message,
                when=secs,
                data={"telegram_id": telegram_id, "day": day},
                name=f"day{day}_{telegram_id}",
            )
            logger.info(f"♻️ بازیابی روز {day} برای {telegram_id}")


async def post_init(app: Application):
    await restore_scheduled_jobs(app)


# ---------- main ----------
def main():
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],

        allow_reentry=True,
    )

    # اول مکالمه 
    app.add_handler(conv_handler)

    #app.add_handler(CommandHandler("start", start))  
    app.add_handler(CommandHandler("cancel", cancel))          
    app.add_handler(CommandHandler("restart", restart))       

    print("🤖 ربات در حال اجراست... (Ctrl+C برای توقف)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
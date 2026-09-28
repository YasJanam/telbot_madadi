import logging
from datetime import datetime, timedelta

from telegram.ext import Application, ContextTypes

from config import DAY_1_MESSAGE, DAY_2_MESSAGE, DAY_3_MESSAGE
from services.database import mark_day_sent, get_users_for_restore


logger = logging.getLogger(__name__)

DAY_1_DELAY = timedelta(days=1)
DAY_2_DELAY = timedelta(days=2)
DAY_3_DELAY = timedelta(days=3)


def schedule_scenario(app, telegram_id, joined_at=None):
    """زمان‌بندی سه پیام برای کاربر"""
    if app is None or app.job_queue is None:
        logger.error("❌ app یا job_queue در دسترس نیست!")
        return

    if joined_at is None:
        joined_at = datetime.now()
    elif isinstance(joined_at, str):
        try:
            joined_at = datetime.strptime(joined_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            joined_at = datetime.now()

    # پاک کردن jobهای قبلی
    for day in (1, 2, 3):
        for job in app.job_queue.get_jobs_by_name(f"day{day}_{telegram_id}"):
            job.schedule_removal()

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
        logger.info(f"⏰ روز {day} برای {telegram_id} → {seconds_until:.0f} ثانیه دیگه")


async def send_day_message(context: ContextTypes.DEFAULT_TYPE):
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
        logger.exception(f"❌ خطا در ارسال روز {day}: {e}")


async def restore_scheduled_jobs(app: Application):
    """بعد از ری‌استارت، jobها رو دوباره بساز"""
    users = get_users_for_restore()
    logger.info(f"♻️ {len(users)} کاربر برای بازیابی")

    for telegram_id, joined_at, d1, d2, d3 in users:
        if d1 and d2 and d3:
            continue

        try:
            joined_at_dt = datetime.strptime(joined_at, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            joined_at_dt = datetime.now()

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
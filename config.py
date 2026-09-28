import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = "users_telbot.db"

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


SHEET_ID = os.getenv("SHEET_ID")
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')

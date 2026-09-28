import logging

from telegram import Update
from telegram.ext import Application

from config import BOT_TOKEN
from services.database import init_db
from services.scenario import restore_scheduled_jobs

from handlers import start, cancel, quiz, register


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    await restore_scheduled_jobs(app)


def main():
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    start.register(app)
    cancel.register(app)
    register.register(app)
    quiz.register(app)

    print("🤖 ربات در حال اجراست... (Ctrl+C برای توقف)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
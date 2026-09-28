from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler

from services.database import delete_user

"""
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "لغو شد. هر وقت خواستی /start بزن.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

"""

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    delete_user(user.id)

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


def register(app):
    #app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("restart", restart))
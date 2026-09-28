from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import GIFT_LINK
from services.database import save_user, get_user
from services.scenario import schedule_scenario


FULL_NAME, PHONE = range(2)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing = get_user(user.id)

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

    save_user(user.id, user.username, full_name, phone)

    await message.reply_text(
        "✅ ثبت‌نامت با موفقیت انجام شد!\n\n"
        f"👤 نام: {full_name}\n"
        f"📞 شماره: {phone}\n\n"
        "📅 از امروز، به مدت ۳ روز، هر روز یه محتوای ویژه 🎁 برات می‌فرستیم. منتظر باش!",
        reply_markup=ReplyKeyboardRemove(),
    )

    schedule_scenario(context.application, user.id, datetime.now())

    context.user_data.clear()
    return ConversationHandler.END



def register(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_from_start)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)


async def cancel_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "لغو شد. هر وقت خواستی /register بزن.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END
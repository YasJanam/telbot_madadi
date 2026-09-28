from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from services.database import get_user


# ---------- دکمه‌های اصلی ----------
def get_main_keyboard(is_registered: bool):
  
    keyboard = [
        [
            InlineKeyboardButton("📝 آزمون‌ها", callback_data="help_quiz"),
            InlineKeyboardButton("📋 اطلاعات من", callback_data="help_myinfo"),
        ],
    ]

    if not is_registered:
        keyboard.insert(0, [
            InlineKeyboardButton("✍️ ثبت‌نام", callback_data="help_register")
        ])

    keyboard.append([
        InlineKeyboardButton("🎁 هدایا و سناریو", callback_data="help_gifts"),
        InlineKeyboardButton("❓ سوالات متداول", callback_data="help_faq"),
    ])

    return InlineKeyboardMarkup(keyboard)


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user = update.effective_user
    existing = get_user(user.id)

    if existing:
        welcome = (
            f"سلام {existing[0]} 👋\n\n"
            "خوش برگشتی!\n"
            "یکی از گزینه‌ها رو انتخاب کن:"
        )
    else:
        welcome = (
            f"سلام {user.first_name} 👋\n\n"
            "به ربات ما خوش آمدی! 🎉\n\n"
            "برای شروع، یکی از گزینه‌ها رو انتخاب کن:"
        )

    await update.message.reply_text(
        welcome,
        reply_markup=get_main_keyboard(is_registered=bool(existing)),
        parse_mode="Markdown",
    )


# ---------- /help ----------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)

    await update.message.reply_text(
        "📖 **راهنما**\n\n"
        "یکی از موضوعات زیر رو انتخاب کن:",
        reply_markup=get_main_keyboard(is_registered=bool(existing)),
        parse_mode="Markdown",
    )


# ---------- Callback: نمایش راهنماها ----------
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
   
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "help_register":
        text = (
            "✍️ **ثبت‌نام**\n\n"
            "برای ثبت‌نام کافیه:\n"
            "1️⃣ دستور /register رو بزنی\n"
            "2️⃣ اسم و فامیلت رو بفرستی\n"
            "3️⃣ شماره تلفنت رو ارسال کنی\n\n"
            "بعد از ثبت‌نام، یه هدیه‌ی خوش‌آمدگویی و ۳ روز محتوای ویژه دریافت می‌کنی! 🎁"
        )

    elif data == "help_quiz":
        text = (
            "📝 **آزمون‌ها**\n\n"
            "با دستور /quiz می‌تونی:\n"
            "• لیست آزمون‌های موجود رو ببینی\n"
            "• آزمون موردنظر رو انتخاب کنی\n"
            "• به سوالات چهارگزینه‌ای جواب بدی\n"
            "• نتیجه‌ی نهایی رو ببینی\n\n"
            "برای شروع: /quiz"
        )

    elif data == "help_myinfo":
        text = (
            "📋 **اطلاعات من**\n\n"
            "با دستور /myinfo می‌تونی:\n"
            "• اسم و شماره‌ی ثبت‌شده‌ت رو ببینی\n"
            "• تاریخ ثبت‌نامت رو چک کنی\n"
            "• وضعیت هدایای ۳ روزه رو ببینی\n\n"
            "برای دیدن: /myinfo"
        )

    elif data == "help_gifts":
        text = (
            "🎁 **هدایا و سناریو**\n\n"
            "بعد از ثبت‌نام، این هدایا رو دریافت می‌کنی:\n\n"
            "🎁 **هدیه‌ی خوش‌آمدگویی** — بلافاصله\n"
            "🎬 **روز اول** — ۲۴ ساعت بعد\n"
            "🎬 **روز دوم** — ۴۸ ساعت بعد\n"
            "🎁 **روز سوم** — ۷۲ ساعت بعد (هدیه‌ی نهایی)\n\n"
            "برای شروع، /register رو بزن."
        )

    elif data == "help_faq":
        text = (
            "❓ **سوالات متداول**\n\n"
            "**چطور ثبت‌نام کنم؟**\n"
            "دستور /register رو بزن.\n\n"
            "**چطور اطلاعاتم رو پاک کنم؟**\n"
            "دستور /restart رو بزن.\n\n"
            "**آزمون‌ها چطور کار می‌کنن؟**\n"
            "دستور /quiz رو بزن، یه آزمون انتخاب کن.\n\n"
            "**هدایا کِی میاد؟**\n"
            "بعد از ثبت‌نام، به مدت ۳ روز هر روز یه محتوا."
        )

    else:
        text = "❌ گزینه نامشخص."

    # دکمه‌ی برگشت
    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت به منوی اصلی", callback_data="help_back")]
    ])

    await query.edit_message_text(
        text,
        reply_markup=back_keyboard,
        parse_mode="Markdown",
    )


async def help_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    existing = get_user(user_id)

    await query.edit_message_text(
        "📖 **راهنما**\n\n"
        "یکی از موضوعات زیر رو انتخاب کن:",
        reply_markup=get_main_keyboard(is_registered=bool(existing)),
        parse_mode="Markdown",
    )


# ---------- ثبت هندلرها ----------
def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Callbackها
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help_(register|quiz|myinfo|gifts|faq)$"))
    app.add_handler(CallbackQueryHandler(help_back_callback, pattern=r"^help_back$"))
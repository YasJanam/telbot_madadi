import asyncio
import json
import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


logger = logging.getLogger(__name__)

QUIZ_DIR = Path("quizzes")
quiz_states = {}

MAX_OPTIONS = 10


# ---------- توابع کمکی ----------
def list_quizzes():
    """لیست آزمون‌های موجود"""
    if not QUIZ_DIR.exists():
        QUIZ_DIR.mkdir(parents=True, exist_ok=True)
        return []
    return sorted([f.stem for f in QUIZ_DIR.glob("*.json")])


def load_quiz(quiz_name: str):
    file_path = QUIZ_DIR / f"{quiz_name}.json"

    if not file_path.exists():
        logger.warning(f"فایل کوییز پیدا نشد: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"خطا در لود کوییز {quiz_name}: {e}")
        return None

    if not isinstance(data, dict) or "questions" not in data:
        logger.error(f"کوییز {quiz_name} ساختار درست نداره")
        return None

    questions = data["questions"]
    if not questions:
        logger.error(f"کوییز {quiz_name} هیچ سوالی نداره")
        return None

    for i, q in enumerate(questions):
        # چک وجود فیلدها
        if "question" not in q or "options" not in q or "scores" not in q:
            logger.error(f"سوال {i+1} کوییز {quiz_name} ناقصه")
            return None

        options = q["options"]
        scores = q["scores"]

        if not isinstance(options, list) or not isinstance(scores, list):
            logger.error(f"سوال {i+1} کوییز {quiz_name}: options/scores باید لیست باشن")
            return None

        if len(options) < 2:
            logger.error(f"سوال {i+1} کوییز {quiz_name}: حداقل ۲ گزینه لازمه")
            return None

        if len(options) > MAX_OPTIONS:
            logger.error(f"سوال {i+1} کوییز {quiz_name}: حداکثر {MAX_OPTIONS} گزینه")
            return None

    
        if len(options) != len(scores):
            logger.error(
                f"سوال {i+1} کوییز {quiz_name}: "
                f"تعداد options ({len(options)}) و scores ({len(scores)}) برابر نیست"
            )
            return None

        if not all(isinstance(s, (int, float)) for s in scores):
            logger.error(f"امتیازهای سوال {i+1} کوییز {quiz_name} عددی نیستن")
            return None

        if not all(isinstance(o, str) for o in options):
            logger.error(f"گزینه‌های سوال {i+1} کوییز {quiz_name} رشته نیستن")
            return None

    if "max_total_score" not in data:
        data["max_total_score"] = sum(
            max(q["scores"]) for q in questions
        )

    return data


# ---------- هندلر /quiz ----------
async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع آزمون"""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        quizzes = list_quizzes()

        if not quizzes:
            await update.message.reply_text(
                "❌ هیچ آزمونی موجود نیست.\n"
                "لطفاً فایل JSON توی پوشه‌ی `quizzes/` بذار."
            )
            return

        keyboard = []
        for quiz_name in quizzes:
            data = load_quiz(quiz_name)
            title = data.get("title", quiz_name) if data else quiz_name
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 {title}",
                    callback_data=f"quiz_select_{quiz_name}",
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🧠 کدوم آزمون رو می‌خوای بدی؟",
            reply_markup=reply_markup,
        )
        return

    quiz_name = args[0].lower()
    quiz_data = load_quiz(quiz_name)

    if not quiz_data:
        await update.message.reply_text(
            f"❌ آزمون `{quiz_name}` پیدا نشد.\n"
            f"برای دیدن لیست: /quiz"
        )
        return

    await _start_quiz(context, user_id, quiz_name, quiz_data)


async def quiz_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب آزمون از لیست"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    quiz_name = query.data.replace("quiz_select_", "")

    quiz_data = load_quiz(quiz_name)
    if not quiz_data:
        await query.edit_message_text("❌ آزمون پیدا نشد.")
        return

    title = quiz_data.get("title", quiz_name)
    description = quiz_data.get("description", "")
    total = len(quiz_data["questions"])
    max_score = quiz_data["max_total_score"]

    await query.edit_message_text(
        f"📝 **{title}**\n\n"
        f"{description}\n\n"
        f"📊 تعداد سوالات: {total}\n"
        f"💯 حداکثر امتیاز: {max_score}\n\n"
        "بزن بریم! 🚀",
        parse_mode="Markdown",
    )

    await asyncio.sleep(1)
    await _start_quiz(context, user_id, quiz_name, quiz_data)


async def _start_quiz(context, user_id: int, quiz_name: str, quiz_data: dict):
    """شروع آزمون"""
    quiz_states[user_id] = {
        "quiz": quiz_data,
        "quiz_name": quiz_name,
        "current": 0,
        "total_score": 0,
    }

    await _send_question(context, user_id)


async def _send_question(context, user_id: int):
    """ارسال سوال فعلی با تعداد گزینه‌های داینامیک"""
    state = quiz_states.get(user_id)
    if not state:
        return

    quiz = state["quiz"]
    current = state["current"]
    total = len(quiz["questions"])

    if current >= total:
        await _send_result(context, user_id)
        return

    q = quiz["questions"][current]
    options = q["options"]

    # 👈 ساخت دکمه‌ها بر اساس تعداد گزینه‌های همین سوال
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([
            InlineKeyboardButton(
                f"{i+1}. {option}",
                callback_data=f"quiz_ans_{i}",
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"❓ **سوال {current + 1} از {total}**\n\n"
        f"{q['question']}"
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def quiz_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش جواب کاربر"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = quiz_states.get(user_id)

    if not state:
        await query.edit_message_text(
            "❌ آزمون منقضی شده. /quiz رو دوباره بزن."
        )
        return

    try:
        option_index = int(query.data.replace("quiz_ans_", ""))
    except ValueError:
        return

    quiz = state["quiz"]
    current = state["current"]

    if not (0 <= current < len(quiz["questions"])):
        return

    q = quiz["questions"][current]
    options = q["options"]
    scores = q["scores"]

    # 👈 چک داینامیک: ایندکس باید توی محدوده‌ی گزینه‌های همین سوال باشه
    if not (0 <= option_index < len(options)):
        return

    option_score = scores[option_index]
    state["total_score"] += option_score

    selected_text = options[option_index]

    text = (
        f"❓ **سوال {current + 1} از {len(quiz['questions'])}**\n\n"
        f"{q['question']}\n\n"
        f"✅ انتخاب تو: {selected_text}\n"
        f"💯 امتیاز این پاسخ: **{option_score}**"
    )

    await query.edit_message_text(text, parse_mode="Markdown")

    state["current"] += 1

    await asyncio.sleep(2)
    await _send_question(context, user_id)



def get_result_message(quiz_data: dict, percentage: float) -> dict:
    """
    انتخاب پیام مناسب بر اساس درصد.
    اگه result_messages تعریف نشده باشه، پیام پیش‌فرض برمی‌گردونه.
    """
    messages = quiz_data.get("result_messages")

    if messages:
        # مرتب‌سازی نزولی
        sorted_msgs = sorted(
            messages, key=lambda m: m["min_percent"], reverse=True
        )
        for msg in sorted_msgs:
            if percentage >= msg["min_percent"]:
                return {
                    "emoji": msg.get("emoji", "📊"),
                    "title": msg.get("title", ""),
                    "message": msg.get("message", ""),
                }

    # پیام پیش‌فرض (اگه result_messages نبود یا هیچ‌کدوم match نشد)
    if percentage >= 80:
        return {"emoji": "🏆", "title": "", "message": "فوق‌العاده! تو یه استاد هستی!"}
    elif percentage >= 60:
        return {"emoji": "👍", "title": "", "message": "خوب بود! ولی هنوز جا برای پیشرفت داری."}
    elif percentage >= 40:
        return {"emoji": "📚", "title": "", "message": "بد نبود، ولی بهتره یه بار دیگه مطالب رو مرور کنی."}
    else:
        return {"emoji": "💪", "title": "", "message": "نگران نباش! با تمرین بهتر می‌شی."}
    


async def _send_result(context, user_id: int):
    state = quiz_states.get(user_id)
    if not state:
        return

    score = state["total_score"]
    quiz_data = state["quiz"]
    max_score = quiz_data["max_total_score"]
    percentage = (score / max_score) * 100 if max_score > 0 else 0

    # 👈 گرفتن پیام مناسب از فایل JSON
    result = get_result_message(quiz_data, percentage)

    emoji = result["emoji"]
    title = result["title"]
    message = result["message"]

    # ساخت متن نهایی
    text_parts = [f"{emoji} **آزمون تموم شد!**\n"]

    if title:
        text_parts.append(f"**{title}**\n")

    text_parts.append(
        f"\n💯 امتیاز تو: **{score}** از {max_score}\n"
        f"📈 درصد: **{percentage:.0f}%**\n"
    )

    if message:
        text_parts.append(f"\n{message}")

    keyboard = [
        [InlineKeyboardButton("🔄 آزمون مجدد", callback_data="quiz_retry")]
    ]

    await context.bot.send_message(
        chat_id=user_id,
        text="\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

    quiz_states.pop(user_id, None)



async def quiz_retry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quizzes = list_quizzes()
    if not quizzes:
        await query.edit_message_text("❌ هیچ آزمونی موجود نیست.")
        return

    keyboard = []
    for quiz_name in quizzes:
        data = load_quiz(quiz_name)
        title = data.get("title", quiz_name) if data else quiz_name
        keyboard.append([
            InlineKeyboardButton(
                f"📝 {title}",
                callback_data=f"quiz_select_{quiz_name}",
            )
        ])

    await query.edit_message_text(
        "🧠 کدوم آزمون رو می‌خوای بدی؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- ثبت هندلرها ----------
def register(app):
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(
        CallbackQueryHandler(quiz_select_callback, pattern=r"^quiz_select_")
    )
    app.add_handler(
        CallbackQueryHandler(quiz_answer_callback, pattern=r"^quiz_ans_")
    )
    app.add_handler(
        CallbackQueryHandler(quiz_retry_callback, pattern=r"^quiz_retry$")
    )
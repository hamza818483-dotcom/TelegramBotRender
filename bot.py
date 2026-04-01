import os
import io
import asyncio
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, OWNER_ID
from permissions import is_permitted, permit_user, revoke_user, list_permitted
from gemini_helper import (
    generate_mcq_from_image,
    generate_mcq_from_text,
    extract_mcq_from_text
)
from pdf_helper import (
    extract_text_from_pdf,
    get_pdf_page_count,
    get_pdf_first_page_image
)
from csv_manager import save_mcqs_to_csv, load_mcqs_from_csv
from poll_sender import send_polls_batch, send_poll_to_chat
from arg_parser import parse_pdf_command
from quiz_scheduler import save_quiz, get_quiz, delete_quiz, list_quizzes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User state tracking (in-memory)
user_states = {}


def check_permission(user_id: int) -> bool:
    return is_permitted(user_id)


# ─────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Handle quiz deep link: /start quiz_XXXX
    if context.args and context.args[0].startswith("quiz_"):
        quiz_id = context.args[0].replace("quiz_", "")
        if check_permission(user.id):
            quiz = get_quiz(quiz_id)
            if quiz:
                await update.message.reply_text(
                    f"📋 *{quiz['name']}*\n"
                    f"📊 {quiz['mcq_count']} MCQ\n"
                    f"⏱️ Interval: {quiz['interval']}s\n\n"
                    f"শুরু করবেন?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("▶️ শুরু করো", callback_data=f"startquiz|{quiz_id}|{user.id}")
                    ]])
                )
                return

    if not check_permission(user.id):
        await update.message.reply_text(
            "❌ আপনার এই বট ব্যবহারের অনুমতি নেই।\nBot owner এর কাছে access চাইন।"
        )
        return

    text = (
        f"👋 *স্বাগতম, {user.first_name}!*\n\n"
        "🤖 *MCQ Poll Bot* — Gemini AI powered\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📷 *Image থেকে MCQ:*\n"
        "ছবি পাঠান → `/image [prompt]`\n\n"
        "📄 *PDF → AI MCQ:*\n"
        "`/pdfm -p 1-10 -m \"Title\" [prompt]`\n\n"
        "📋 *PDF → হুবহু MCQ তোলা:*\n"
        "`/qbm -p 1-10 -m \"Title\"`\n\n"
        "📊 *CSV থেকে Poll:*\n"
        "`/sendcsv` → CSV পাঠান\n\n"
        "🔗 *Scheduled Quiz:*\n"
        "`/quizlink` → সেটআপ করুন\n\n"
        "👥 *Access:*\n"
        "`/permit [user_id]` | `/revoke [user_id]`\n\n"
        "ℹ️ `/help` — বিস্তারিত\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─────────────────────────────────────────────────────────
# /help
# ─────────────────────────────────────────────────────────
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return

    text = (
        "📖 *সম্পূর্ণ সাহায্য*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📷 *IMAGE:*\n"
        "১. ছবি পাঠান\n"
        "২. `/image বাংলায় ৫টি MCQ বানাও`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📄 *PDF Parameters:*\n"
        "`-p 1-10` — পেজ রেঞ্জ *(বাধ্যতামূলক)*\n"
        "`-c @channel` — চ্যানেল target\n"
        "`-m \"Title\"` — টাইটেল *(বাধ্যতামূলক)*\n"
        "`-t topic_id` — Forum topic\n"
        "`-i` — প্রথম পেজের ছবি সহ\n"
        "`[prompt]` — AI prompt\n\n"
        "*উদাহরণ:*\n"
        "`/pdfm -p 1-5 -c @ch -m \"Ch1\" বাংলায়`\n"
        "`/qbm -p 10-20 -m \"MCQ Bank\"`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 *CSV Poll:*\n"
        "`/sendcsv` → CSV পাঠান → চ্যানেল বেছে নিন\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 *Quiz Link:*\n"
        "`/quizlink` → CSV → নাম/description/interval/channel সেট করুন\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 *Admin (Owner only):*\n"
        "`/permit 123456` | `/revoke 123456` | `/listusers`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─────────────────────────────────────────────────────────
# PERMISSION COMMANDS
# ─────────────────────────────────────────────────────────
async def permit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ শুধু bot owner পারবে।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: `/permit [user_id]`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ সঠিক User ID দিন।")
        return
    if permit_user(uid):
        await update.message.reply_text(f"✅ User `{uid}` কে access দেওয়া হয়েছে।", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"ℹ️ আগে থেকেই permitted।", parse_mode=ParseMode.MARKDOWN)


async def revoke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ শুধু bot owner পারবে।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: `/revoke [user_id]`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ সঠিক User ID দিন।")
        return
    if revoke_user(uid):
        await update.message.reply_text(f"✅ Access নেওয়া হয়েছে।", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"ℹ️ Permitted ছিল না।", parse_mode=ParseMode.MARKDOWN)


async def listusers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    users = list_permitted()
    if not users:
        await update.message.reply_text("📋 কোনো permitted user নেই।")
        return
    text = "👥 *Permitted Users:*\n" + "\n".join(f"• `{u}`" for u in users)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─────────────────────────────────────────────────────────
# IMAGE FLOW
# ─────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    user_states[user_id] = {
        "waiting_for": "image_command",
        "image_bytes": buf.getvalue(),
        "mime_type": "image/jpeg",
    }
    await update.message.reply_text(
        "✅ ছবি পাওয়া গেছে!\nএখন লিখুন: `/image [prompt]`\n\nযেমন: `/image বাংলায় ৫টি MCQ বানাও`",
        parse_mode=ParseMode.MARKDOWN
    )


async def image_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    if state.get("waiting_for") != "image_command":
        await update.message.reply_text("❌ আগে একটি ছবি পাঠান।")
        return
    prompt = " ".join(context.args) if context.args else ""
    status_msg = await update.message.reply_text("🔄 AI MCQ তৈরি করছে...")
    try:
        mcqs = await asyncio.get_event_loop().run_in_executor(
            None, lambda: generate_mcq_from_image(
                state["image_bytes"], state["mime_type"], prompt
            )
        )
        if not mcqs:
            await status_msg.edit_text("❌ MCQ তৈরি করা যায়নি।")
            return
        title = prompt[:30] if prompt else "image_quiz"
        csv_path = save_mcqs_to_csv(mcqs, title)
        user_states.pop(user_id, None)
        await status_msg.edit_text(
            f"✅ *{len(mcqs)}টি MCQ তৈরি হয়েছে!*\n\nএখন কী করবেন?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_poll_action_keyboard(csv_path, update.effective_chat.id)
        )
    except Exception as e:
        logger.error(f"Image MCQ error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


# ─────────────────────────────────────────────────────────
# PDF FLOW
# ─────────────────────────────────────────────────────────
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    doc = update.message.document
    if not doc:
        return

    filename = doc.file_name or ""

    # PDF
    if filename.lower().endswith(".pdf"):
        status_msg = await update.message.reply_text("📥 PDF লোড হচ্ছে...")
        file = await context.bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        pdf_bytes = buf.getvalue()
        page_count = get_pdf_page_count(pdf_bytes)
        user_states[update.effective_user.id] = {
            "waiting_for": "pdf_command",
            "pdf_bytes": pdf_bytes,
            "page_count": page_count,
        }
        await status_msg.edit_text(
            f"✅ PDF পাওয়া গেছে! মোট *{page_count}* পেজ।\n\n"
            f"`/pdfm -p 1-{min(10,page_count)} -m \"Title\"`\n"
            f"অথবা\n"
            f"`/qbm -p 1-{min(10,page_count)} -m \"Title\"`",
            parse_mode=ParseMode.MARKDOWN
        )

    # CSV
    elif filename.lower().endswith(".csv"):
        await csv_document_handler(update, context)


async def pdfm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    if state.get("waiting_for") != "pdf_command":
        await update.message.reply_text("❌ আগে একটি PDF পাঠান।")
        return

    args = parse_pdf_command(update.message.text)
    if args.get("error"):
        await update.message.reply_text(
            f"⚠️ কমান্ড ভুল:\n{args['error']}\n\nউদাহরণ: `/pdfm -p 1-10 -m \"Quiz\"`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    pdf_bytes = state["pdf_bytes"]
    page_count = state["page_count"]
    mode = args["mode"]
    page_start = args["page_start"]
    page_end = min(args["page_end"], page_count)
    title = args["title"]
    channel = args.get("channel")
    topic_id = args.get("topic_id")
    include_image = args.get("include_image", False)
    prompt = args.get("prompt", "")

    status_msg = await update.message.reply_text(
        f"🔄 পেজ {page_start}–{page_end} প্রসেস হচ্ছে..."
    )

    try:
        pages_text = extract_text_from_pdf(pdf_bytes, page_start, page_end)
        all_mcqs = []

        for page_num, text in pages_text.items():
            if not text.strip():
                continue
            await status_msg.edit_text(
                f"🔄 পেজ {page_num}/{page_end} প্রসেস...\n✅ এখন পর্যন্ত {len(all_mcqs)}টি MCQ"
            )
            if mode == "qbm":
                mcqs = await asyncio.get_event_loop().run_in_executor(
                    None, lambda t=text: extract_mcq_from_text(t)
                )
            else:
                mcqs = await asyncio.get_event_loop().run_in_executor(
                    None, lambda t=text: generate_mcq_from_text(t, prompt)
                )
            all_mcqs.extend(mcqs)

        if not all_mcqs:
            await status_msg.edit_text("❌ কোনো MCQ তৈরি করা যায়নি।")
            return

        csv_path = save_mcqs_to_csv(all_mcqs, title)
        user_states.pop(user_id, None)

        target_chat = channel if channel else update.effective_chat.id

        if include_image:
            try:
                img_bytes = get_pdf_first_page_image(pdf_bytes)
                await context.bot.send_photo(
                    chat_id=target_chat,
                    photo=io.BytesIO(img_bytes),
                    caption=f"📚 *{title}*",
                    parse_mode=ParseMode.MARKDOWN,
                    message_thread_id=topic_id
                )
            except Exception as e:
                logger.warning(f"Cover image failed: {e}")

        await status_msg.edit_text(
            f"✅ *{len(all_mcqs)}টি MCQ তৈরি!*\n\nএখন কী করবেন?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_poll_action_keyboard(csv_path, target_chat, topic_id)
        )

    except Exception as e:
        logger.error(f"PDF error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


# ─────────────────────────────────────────────────────────
# CSV FLOW
# ─────────────────────────────────────────────────────────
async def sendcsv_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_states[update.effective_user.id] = {"waiting_for": "csv_upload"}
    await update.message.reply_text(
        "📊 CSV ফাইলটি পাঠান (Rayvila format).",
        parse_mode=ParseMode.MARKDOWN
    )


async def csv_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    doc = update.message.document
    if not doc or not (doc.file_name or "").lower().endswith(".csv"):
        return

    waiting = state.get("waiting_for", "")
    if waiting not in ("csv_upload", "quiz_csv"):
        return

    file = await context.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)

    tmp_path = os.path.join("csv_files", f"upload_{user_id}_{datetime.now().strftime('%H%M%S')}.csv")
    with open(tmp_path, "wb") as f:
        f.write(buf.getvalue())

    try:
        mcqs = load_mcqs_from_csv(tmp_path)
    except Exception as e:
        await update.message.reply_text(f"❌ CSV পড়া যায়নি: {e}")
        return

    if not mcqs:
        await update.message.reply_text("❌ CSV তে MCQ নেই।")
        return

    if waiting == "quiz_csv":
        user_states[user_id].update({
            "csv_path": tmp_path,
            "mcqs": mcqs,
            "waiting_for": "quiz_name"
        })
        await update.message.reply_text(
            f"✅ *{len(mcqs)}টি MCQ লোড হয়েছে।*\n\nQuiz এর নাম লিখুন:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    user_states.pop(user_id, None)
    await update.message.reply_text(
        f"✅ *{len(mcqs)}টি MCQ লোড!*\n\nকোথায় পাঠাবেন?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_poll_action_keyboard(tmp_path, update.effective_chat.id)
    )


# ─────────────────────────────────────────────────────────
# QUIZ LINK FLOW
# ─────────────────────────────────────────────────────────
async def quizlink_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return
    user_states[update.effective_user.id] = {"waiting_for": "quiz_csv"}
    await update.message.reply_text(
        "🔗 *Quiz Setup*\n\nপ্রথমে CSV ফাইল পাঠান।",
        parse_mode=ParseMode.MARKDOWN
    )


async def startquiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return

    if not context.args:
        quizzes = list_quizzes()
        if not quizzes:
            await update.message.reply_text("📋 কোনো quiz নেই। `/quizlink` দিয়ে তৈরি করুন।")
            return
        text = "📋 *আপনার Quizzes:*\n\n"
        buttons = []
        for q in quizzes:
            text += f"• *{q['name']}* — {q['mcq_count']} MCQ\n"
            buttons.append([InlineKeyboardButton(
                f"▶️ {q['name']}",
                callback_data=f"startquiz|{q['id']}|{update.effective_user.id}"
            )])
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(buttons))
        return

    quiz_id = context.args[0].replace("quiz_", "")
    quiz = get_quiz(quiz_id)
    if not quiz:
        await update.message.reply_text("❌ Quiz পাওয়া যায়নি।")
        return

    await update.message.reply_text(f"▶️ *{quiz['name']}* শুরু হচ্ছে...", parse_mode=ParseMode.MARKDOWN)
    asyncio.create_task(run_scheduled_quiz(context.bot, quiz, update.effective_chat.id))


# ─────────────────────────────────────────────────────────
# TEXT HANDLER (multi-step flows)
# ─────────────────────────────────────────────────────────
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permission(update.effective_user.id):
        return

    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    waiting = state.get("waiting_for", "")
    text = update.message.text.strip()

    if waiting == "channel_input":
        channel = text
        csv_path = state["csv_path"]
        user_states.pop(user_id, None)
        try:
            mcqs = load_mcqs_from_csv(csv_path)
        except Exception as e:
            await update.message.reply_text(f"❌ CSV error: {e}")
            return
        await update.message.reply_text(f"📤 `{channel}` তে পাঠানো শুরু...", parse_mode=ParseMode.MARKDOWN)
        success, fail = await send_polls_batch(context.bot, channel, mcqs, delay=1.0)
        await update.message.reply_text(
            f"✅ সম্পন্ন!\n✔️ সফল: {success}\n❌ ব্যর্থ: {fail}",
            parse_mode=ParseMode.MARKDOWN
        )

    elif waiting == "quiz_name":
        user_states[user_id]["quiz_name"] = text
        user_states[user_id]["waiting_for"] = "quiz_description"
        await update.message.reply_text("📝 Description লিখুন (বা /skip):")

    elif waiting == "quiz_description":
        user_states[user_id]["quiz_description"] = "" if text == "/skip" else text
        user_states[user_id]["waiting_for"] = "quiz_interval"
        await update.message.reply_text(
            "⏱️ কত সেকেন্ড পর পর Poll পাঠাবে?\n_(যেমন: 30)_",
            parse_mode=ParseMode.MARKDOWN
        )

    elif waiting == "quiz_interval":
        try:
            interval = max(5, int(text))
        except ValueError:
            await update.message.reply_text("❌ সংখ্যা দিন।")
            return
        user_states[user_id]["quiz_interval"] = interval
        user_states[user_id]["waiting_for"] = "quiz_channel"
        await update.message.reply_text(
            "📢 Channel username বা ID দিন (যেমন: `@mychannel`):",
            parse_mode=ParseMode.MARKDOWN
        )

    elif waiting == "quiz_channel":
        import uuid
        quiz_id = str(uuid.uuid4())[:8]
        mcqs = state.get("mcqs", [])
        csv_path = state.get("csv_path", "")
        quiz_data = {
            "id": quiz_id,
            "name": state.get("quiz_name", "Quiz"),
            "description": state.get("quiz_description", ""),
            "interval": state.get("quiz_interval", 30),
            "channel": text,
            "csv_path": csv_path,
            "mcq_count": len(mcqs),
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
        }
        save_quiz(quiz_id, quiz_data)
        user_states.pop(user_id, None)

        bot_info = await context.bot.get_me()
        await update.message.reply_text(
            f"✅ *Quiz সেটআপ সম্পন্ন!*\n\n"
            f"📛 নাম: *{quiz_data['name']}*\n"
            f"📊 MCQ: *{len(mcqs)}টি*\n"
            f"⏱️ Interval: *{quiz_data['interval']}s*\n"
            f"📢 Channel: *{text}*\n\n"
            f"🔗 Quiz link:\n`https://t.me/{bot_info.username}?start=quiz_{quiz_id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ এখনই শুরু করো", callback_data=f"startquiz|{quiz_id}|{user_id}")
            ]])
        )


# ─────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not check_permission(user_id):
        await query.edit_message_text("❌ Permission নেই।")
        return

    parts = query.data.split("|")
    action = parts[0]

    if action == "sendpoll":
        csv_path = parts[1]
        target_chat = parts[2]
        topic_id = int(parts[3]) if len(parts) > 3 and parts[3] else None

        try:
            mcqs = load_mcqs_from_csv(csv_path)
        except Exception as e:
            await query.edit_message_text(f"❌ CSV error: {e}")
            return

        await query.edit_message_text(f"📤 *{len(mcqs)}টি Poll পাঠানো হচ্ছে...*", parse_mode=ParseMode.MARKDOWN)
        progress_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ শুরু হচ্ছে...")
        last = [0]

        async def prog(cur, tot):
            pct = int(cur / tot * 100)
            if pct - last[0] >= 10 or cur == tot:
                last[0] = pct
                bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                try:
                    await progress_msg.edit_text(f"⏳ [{bar}] {pct}% ({cur}/{tot})")
                except Exception:
                    pass

        success, fail = await send_polls_batch(
            context.bot, target_chat, mcqs,
            message_thread_id=topic_id, delay=1.0, progress_callback=prog
        )
        await progress_msg.edit_text(
            f"✅ *সম্পন্ন!*\n✔️ সফল: {success}\n❌ ব্যর্থ: {fail}",
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "downloadcsv":
        csv_path = parts[1]
        try:
            with open(csv_path, "rb") as f:
                data = f.read()
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=io.BytesIO(data),
                filename=os.path.basename(csv_path),
                caption="📊 আপনার CSV ফাইল"
            )
            await query.edit_message_text("✅ CSV পাঠানো হয়েছে।")
        except Exception as e:
            await query.edit_message_text(f"❌ CSV পাঠানো যায়নি: {e}")

    elif action == "choosechannel":
        csv_path = parts[1]
        user_states[user_id] = {"waiting_for": "channel_input", "csv_path": csv_path}
        await query.edit_message_text(
            "📢 চ্যানেল/গ্রুপের username বা ID দিন:\n_(যেমন: @mychannel বা -100xxxxxxxx)_",
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "startquiz":
        quiz_id = parts[1]
        quiz = get_quiz(quiz_id)
        if not quiz:
            await query.edit_message_text("❌ Quiz পাওয়া যায়নি।")
            return
        await query.edit_message_text(
            f"▶️ *{quiz['name']}* শুরু হচ্ছে...\n📢 {quiz['channel']}\n⏱️ {quiz['interval']}s interval",
            parse_mode=ParseMode.MARKDOWN
        )
        asyncio.create_task(run_scheduled_quiz(context.bot, quiz, update.effective_chat.id))


# ─────────────────────────────────────────────────────────
# SCHEDULED QUIZ
# ─────────────────────────────────────────────────────────
async def run_scheduled_quiz(bot, quiz: dict, notify_chat_id: int):
    try:
        mcqs = load_mcqs_from_csv(quiz["csv_path"])
        channel = quiz["channel"]
        interval = quiz["interval"]
        for i, mcq in enumerate(mcqs):
            await send_poll_to_chat(bot, channel, mcq)
            if i < len(mcqs) - 1:
                await asyncio.sleep(interval)
        await bot.send_message(
            chat_id=notify_chat_id,
            text=f"✅ *{quiz['name']}* শেষ! মোট {len(mcqs)}টি Poll পাঠানো হয়েছে।",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        try:
            await bot.send_message(chat_id=notify_chat_id, text=f"❌ Quiz error: {str(e)[:200]}")
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# KEYBOARD HELPER
# ─────────────────────────────────────────────────────────
def _poll_action_keyboard(csv_path: str, target_chat, topic_id=None):
    cb_send = f"sendpoll|{csv_path}|{target_chat}"
    if topic_id:
        cb_send += f"|{topic_id}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 এখনই Poll পাঠাও", callback_data=cb_send),
            InlineKeyboardButton("📁 CSV ডাউনলোড", callback_data=f"downloadcsv|{csv_path}"),
        ],
        [
            InlineKeyboardButton("📢 অন্য চ্যানেলে পাঠাও", callback_data=f"choosechannel|{csv_path}"),
        ]
    ])


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("permit", permit_handler))
    app.add_handler(CommandHandler("revoke", revoke_handler))
    app.add_handler(CommandHandler("listusers", listusers_handler))
    app.add_handler(CommandHandler("image", image_command_handler))
    app.add_handler(CommandHandler("pdfm", pdfm_handler))
    app.add_handler(CommandHandler("qbm", pdfm_handler))
    app.add_handler(CommandHandler("sendcsv", sendcsv_handler))
    app.add_handler(CommandHandler("quizlink", quizlink_handler))
    app.add_handler(CommandHandler("startquiz", startquiz_command))

    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("🤖 Bot চালু হয়েছে!")
    PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = f"https://telegrambotrenderlast.onrender.com/{TOKEN}"  # replace with your Render app URL

# Run Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=WEBHOOK_URL
)


if __name__ == "__main__":
    main()

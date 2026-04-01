import asyncio
from telegram import Bot
from telegram.error import TelegramError


async def send_poll_to_chat(
    bot: Bot,
    chat_id,
    mcq: dict,
    message_thread_id: int = None,
    delay: float = 0.5
) -> bool:
    """
    Send a single MCQ as a Telegram Quiz Poll.
    Returns True if successful.
    """
    question = mcq.get("question", "")
    options = mcq.get("options", [])
    answer_index = mcq.get("answer", 1) - 1  # convert to 0-based
    explanation = mcq.get("explanation", "")

    # Telegram poll question max 300 chars
    if len(question) > 300:
        question = question[:297] + "..."

    # Telegram poll option max 100 chars
    options = [str(o)[:100] for o in options[:4]]

    # Need at least 2 options
    if len(options) < 2:
        return False

    # Clamp answer index
    answer_index = max(0, min(answer_index, len(options) - 1))

    # Explanation max 200 chars
    if len(explanation) > 200:
        explanation = explanation[:197] + "..."

    try:
        kwargs = dict(
            chat_id=chat_id,
            question=question,
            options=options,
            type="quiz",
            correct_option_id=answer_index,
            is_anonymous=True,
        )
        if explanation:
            kwargs["explanation"] = explanation
        if message_thread_id:
            kwargs["message_thread_id"] = message_thread_id

        await bot.send_poll(**kwargs)
        await asyncio.sleep(delay)
        return True

    except TelegramError as e:
        print(f"Poll send error: {e}")
        return False


async def send_polls_batch(
    bot: Bot,
    chat_id,
    mcqs: list,
    message_thread_id: int = None,
    delay: float = 1.0,
    progress_callback=None
) -> tuple:
    """
    Send multiple polls. Returns (success_count, fail_count).
    progress_callback(current, total) called after each poll.
    """
    success = 0
    fail = 0
    total = len(mcqs)

    for i, mcq in enumerate(mcqs):
        ok = await send_poll_to_chat(
            bot, chat_id, mcq,
            message_thread_id=message_thread_id,
            delay=delay
        )
        if ok:
            success += 1
        else:
            fail += 1

        if progress_callback:
            await progress_callback(i + 1, total)

    return success, fail

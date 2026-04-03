import logging
import asyncio
import time

from aiogram import Bot, types
from aiogram.dispatcher.event.bases import SkipHandler

from quiz.models import GroupQuiz

from bot import utils
from bot.utils import redis_group
from bot.utils.redis_group import redis_client
from bot.keyboards import inline_kb

from bot.utils.functions import get_text, generate_user_quiz_data

from .common import animate_texts, delete_quiz_reply_markup
from .statistics import send_statistics


logger = logging.getLogger(__name__)


async def start_group_testing(group_quiz: GroupQuiz, bot: Bot):
    """
    Entry point for starting group quiz testing.
    """
    quiz_id = str(group_quiz.pk)

    await delete_quiz_reply_markup(group_quiz.group_id, group_quiz.message_id, bot)

    animation_msg_id = await animate_texts(group_quiz.group_id, bot)
    await bot.delete_message(group_quiz.group_id, animation_msg_id)

    # Generate once, store in Redis — prevents re-shuffle on continue
    question_data = await generate_user_quiz_data(group_quiz.part)
    await redis_group.store_questions_data(quiz_id, question_data)

    poll_question = await get_text("poll_question")

    await redis_group.set_quiz_active(quiz_id)

    await run_group_quiz_loop(
        group_quiz=group_quiz,
        question_data=question_data,
        poll_question=poll_question,
        timer=group_quiz.part.quiz.timer,
        bot=bot,
    )


async def run_group_quiz_loop(
        group_quiz: GroupQuiz,
        question_data: list,
        poll_question: str,
        timer: int,
        bot: Bot,
        start_index: int = 0
):
    """
    Main loop for sending quiz questions sequentially.
    All per-question state (is_answered, skips) is tracked in Redis —
    no DB reads inside the hot loop.
    """

    quiz_id = str(group_quiz.pk)
    total_questions = len(question_data)

    for index in range(start_index, total_questions):

        # Check if quiz was stopped externally (stop_handler / statistics)
        if not await redis_group.is_quiz_active(quiz_id):
            return

        if index > 0:
            is_answered = await redis_group.is_question_answered(quiz_id)
            if not is_answered:
                skips = await redis_group.increment_skips(quiz_id)
                if skips >= 2:
                    return await handle_no_answers(group_quiz, index, bot)
            # Reset flag for the upcoming question
            await redis_group.reset_question_answered(quiz_id)

        await send_question(
            group_quiz=group_quiz,
            question=question_data[index],
            index=index,
            total_questions=total_questions,
            poll_question=poll_question,
            timer=timer,
            bot=bot,
        )

        await asyncio.sleep(timer + 2)

    await redis_group.set_quiz_inactive(quiz_id)
    await send_statistics(group_quiz.group_id, bot)


async def handle_no_answers(group_quiz: GroupQuiz, index: int, bot: Bot):
    """
    Handles case when nobody answers two questions in a row.
    """
    await redis_group.reset_skips(str(group_quiz.pk))

    text = await get_text("group_noone_answer_to_questions")
    markup = await inline_kb.test_group_continue_markup(group_quiz.group_id, index)

    await bot.send_message(
        chat_id=group_quiz.group_id,
        text=text,
        reply_markup=markup
    )


async def send_question(
        group_quiz: GroupQuiz,
        question: dict,
        index: int,
        total_questions: int,
        poll_question: str,
        timer: int,
        bot: Bot,
):
    """
    Sends a single quiz question and poll.
    """

    question_text = (
        f"<b>[{index + 1}/{total_questions}]. {question['question']}</b>\n\n"
        f"<b>A)</b> {question['options'][0]}\n\n"
        f"<b>B)</b> {question['options'][1]}\n\n"
        f"<b>C)</b> {question['options'][2]}\n\n"
        f"<b>D)</b> {question['options'][3]}\n\n"
    )

    correct_option_id = question["options"].index(question["correct_option"])

    await bot.send_message(
        chat_id=group_quiz.group_id,
        text=question_text
    )

    poll = await bot.send_poll(
        chat_id=group_quiz.group_id,
        question=poll_question,
        options=["A", "B", "C", "D"],
        is_anonymous=False,
        type="quiz",
        correct_option_id=correct_option_id,
        open_period=timer,
        protect_content=True
    )

    group_quiz.poll_id = poll.poll.id
    group_quiz.index = index + 1
    await group_quiz.asave(update_fields=["poll_id", "index"])

    quiz_id = str(group_quiz.pk)

    await redis_group.set_group_question_data(
        group_quiz_id=quiz_id,
        correct_option_id=correct_option_id,
        start_time=time.perf_counter()
    )

    await redis_client.set(
        f"poll:{poll.poll.id}",
        group_quiz.pk,
        ex=3600
    )


async def group_quiz_continue_callback(callback: types.CallbackQuery):
    await callback.answer()

    try:
        _, group_id, index = callback.data.split("_")
        index = int(index)
    except (ValueError, AttributeError):
        return

    group_quiz = await utils.get_group_quiz(group_id)

    if not group_quiz:
        return

    try:
        await callback.message.delete_reply_markup()
    except Exception:
        pass

    quiz_id = str(group_quiz.pk)

    # Restore question order from Redis — no re-shuffle
    question_data = await redis_group.get_questions_data(quiz_id)
    if not question_data:
        # Fallback: Redis key expired (e.g. very long pause), regenerate
        question_data = await generate_user_quiz_data(group_quiz.part)
        await redis_group.store_questions_data(quiz_id, question_data)

    poll_question = await get_text("poll_question")

    await redis_group.reset_skips(quiz_id)
    await redis_group.set_quiz_active(quiz_id)

    asyncio.create_task(
        run_group_quiz_loop(
            group_quiz=group_quiz,
            question_data=question_data,
            poll_question=poll_question,
            timer=group_quiz.part.quiz.timer,
            bot=callback.bot,
            start_index=index
        )
    )


async def testing_group_poll_answer_handler(poll_answer: types.PollAnswer):
    try:
        end_time = time.perf_counter()

        # Resolve quiz from poll id
        quiz_id = await redis_client.get(f"poll:{poll_answer.poll_id}")
        if not quiz_id:
            raise SkipHandler()

        # Atomic first-answer detection via SETNX — only first caller triggers DB write
        is_first = await redis_group.set_question_answered(quiz_id)
        if is_first:
            await utils.update_group_quiz_answers(quiz_id)

        # Get question metadata
        q_data = await redis_group.get_group_question_data(quiz_id)
        correct_option_id = q_data["correct_option_id"]
        start_time = q_data["start_time"]

        # Resolve user
        if poll_answer.voter_chat:
            user_id = str(poll_answer.voter_chat.id)
            username = poll_answer.voter_chat.title or str(poll_answer.voter_chat.id)
        else:
            user_id = str(poll_answer.user.id)
            username = (
                f"@{poll_answer.user.username}"
                if poll_answer.user.username
                else poll_answer.user.first_name
            )

        is_correct = (
            len(poll_answer.option_ids) > 0
            and poll_answer.option_ids[0] == correct_option_id
        )

        spent_time = round(end_time - start_time, 2) if start_time else 0.0

        await redis_group.increment_player_score(
            group_quiz_id=quiz_id,
            user_id=user_id,
            is_correct=is_correct,
            spent_time=spent_time,
            username=username
        )

    except SkipHandler:
        raise

    except Exception:
        logger.exception("Poll answer handler error")
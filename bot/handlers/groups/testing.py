import logging

from aiogram import Bot
from aiogram.dispatcher.event.bases import SkipHandler

from quiz.models import GroupQuiz

from bot import utils
from bot.states import QuizState
from bot.utils import redis_group
from bot.keyboards import inline_kb

from bot.utils.functions import get_text, generate_user_quiz_data
from bot.utils.redis_group import redis_client

from .common import animate_texts, delete_quiz_reply_markup
from .statistics import send_statistics


logger = logging.getLogger(__name__)


"""
# UPDATES =============================================== UPDATES
# UPDATES =============================================== UPDATES
# UPDATES =============================================== UPDATES
"""

import asyncio
import time
from aiogram import types
from aiogram.fsm.context import FSMContext


async def start_group_testing(
        group_quiz: GroupQuiz,
        bot: Bot,
        state: FSMContext
):
    """
    Entry point for starting group quiz testing.
    """

    await delete_quiz_reply_markup(group_quiz.group_id, group_quiz.message_id, bot)

    animation_msg_id = await animate_texts(group_quiz.group_id, bot)
    await bot.delete_message(group_quiz.group_id, animation_msg_id)

    await state.set_state(QuizState.group_testing)

    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text("poll_question")

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
        bot,
        start_index: int = 0
):
    """
    Main loop for sending quiz questions sequentially.
    """

    total_questions = len(question_data)

    for index in range(start_index, total_questions):

        # обновляем объект из БД
        await group_quiz.arefresh_from_db()

        if not group_quiz:
            return

        # Проверяем был ли ответ на предыдущий вопрос
        if index != 0 and not group_quiz.is_answered:
            group_quiz.skips += 1
            await group_quiz.asave(update_fields=["skips"])

        # Сброс флага ответа
        if group_quiz.is_answered:
            group_quiz.is_answered = False
            await group_quiz.asave(update_fields=["is_answered"])

        # Проверка на два пропуска
        if group_quiz.skips >= 2:
            await handle_no_answers(group_quiz, index, bot)
            return

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

    await send_statistics(group_quiz.group_id, bot)


async def handle_no_answers(group_quiz: GroupQuiz, index: int, bot):
    """
    Handles case when nobody answers two questions in a row.
    """

    group_quiz.skips = 0
    await group_quiz.asave(update_fields=["skips"])

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
        bot,
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

    await redis_group.set_group_question_data(
        group_quiz_id=str(group_quiz.pk),
        correct_option_id=correct_option_id,
        start_time=time.perf_counter()
    )

    await redis_client.set(
        f"poll:{poll.poll.id}",
        group_quiz.pk,
        ex=3600
    )


async def group_quiz_continue_callback(
        callback: types.CallbackQuery,
        state: FSMContext
):
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

    question_data = await generate_user_quiz_data(group_quiz.part)

    poll_question = await get_text("poll_question")

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

        # -----------------------------
        # FIND QUIZ FROM REDIS
        # -----------------------------
        quiz_id = await redis_client.get(f"poll:{poll_answer.poll_id}")

        if not quiz_id:
            raise SkipHandler()

        # -----------------------------
        # GET QUESTION DATA
        # -----------------------------
        q_data = await redis_group.get_group_question_data(quiz_id)

        correct_option_id = q_data["correct_option_id"]
        start_time = q_data["start_time"]

        # -----------------------------
        # USER INFO
        # -----------------------------
        user_id = str(poll_answer.user.id)

        if poll_answer.voter_chat:
            user_id = str(poll_answer.voter_chat.id)

        username = (
            f"@{poll_answer.user.username}"
            if poll_answer.user.username
            else poll_answer.user.first_name
        )

        # -----------------------------
        # CHECK ANSWER
        # -----------------------------
        is_correct = (
            len(poll_answer.option_ids) > 0
            and poll_answer.option_ids[0] == correct_option_id
        )

        spent_time = round(end_time - start_time, 2) if start_time else 0.0

        # -----------------------------
        # UPDATE REDIS SCORE
        # -----------------------------
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



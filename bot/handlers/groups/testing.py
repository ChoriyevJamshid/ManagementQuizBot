
import time
from aiogram import types
from aiogram.fsm.context import FSMContext

from quiz.models import GroupQuiz

from bot import utils
from bot.states import QuizState
from bot.utils.functions import get_text, generate_user_quiz_data
from bot.utils import redis_group
from .send_test import send_tests_by_recurse
from .common import animate_texts, delete_quiz_reply_markup


async def testing_send_tests_by_recurse(group_quiz: GroupQuiz, callback: types.CallbackQuery, state: FSMContext):
    await delete_quiz_reply_markup(group_quiz.group_id, group_quiz.message_id, callback)
    message_id = await animate_texts(group_quiz.group_id, callback)

    await callback.bot.delete_message(chat_id=group_quiz.group_id, message_id=message_id)
    await state.set_state(QuizState.group_testing)

    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question')

    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=0,
        question_data=question_data,
        poll_question=poll_question,
        timer=group_quiz.part.quiz.timer,
        callback=callback,
        state=state
    )


async def testing_continue_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    _, group_id, index = callback.data.split('_')
    group_quiz = await utils.get_group_quiz(group_id)

    if not group_quiz:
        return await callback.answer()

    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question')

    await callback.message.delete_reply_markup()
    await callback.answer()

    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=int(index),
        question_data=question_data,
        poll_question=poll_question,
        timer=group_quiz.part.quiz.timer,
        callback=callback,
        state=state
    )


from aiogram.dispatcher.event.bases import SkipHandler
import traceback

async def testing_group_poll_answer_handler(poll_answer: types.PollAnswer):
    try:
        end_time = time.perf_counter()
        
        # DEBUG Logging setup
        with open("poll_debug.log", "a") as f:
            f.write(f"\\n--- Poll Answer Received! User: {poll_answer.user.id}, Poll ID: {poll_answer.poll_id} ---\\n")
        
        group_quiz = await utils.get_group_quiz_by_poll_id(poll_answer.poll_id)

        if not group_quiz:
            with open("poll_debug.log", "a") as f:
                f.write(f"group_quiz not found for poll_id: {poll_answer.poll_id}. Skipping to next handler.\\n")
            raise SkipHandler()

        with open("poll_debug.log", "a") as f:
            f.write(f"Found group_quiz: {group_quiz.pk}, answering: {group_quiz.is_answered}\\n")

        if not group_quiz.is_answered:
            updated = await type(group_quiz).objects.filter(
                pk=group_quiz.pk, is_answered=False
            ).aupdate(
                is_answered=True
            )
            # Fetch the actual database current answers count explicitly, avoiding F expressions that may crash in some db backends
            if updated:
                group_quiz.is_answered = True
                await type(group_quiz).objects.filter(pk=group_quiz.pk).aupdate(
                    answers=group_quiz.answers + 1
                )

        user_id = str(poll_answer.user.id)
        if poll_answer.voter_chat:
            user_id = str(poll_answer.voter_chat.id)

        if poll_answer.user.username:
            username = "@" + poll_answer.user.username
        else:
            username = poll_answer.user.first_name

        q_data = await redis_group.get_group_question_data(str(group_quiz.pk))
        correct_option_id = q_data.get("correct_option_id", 10)
        start_time = q_data.get("start_time", 0.0)

        is_correct = bool(len(poll_answer.option_ids) > 0 and poll_answer.option_ids[0] == correct_option_id)
        spent_time = round(end_time - start_time, 1) if start_time else 0.0

        with open("poll_debug.log", "a") as f:
            f.write(f"Updating Redis - user_id: {user_id}, is_correct: {is_correct}, spent_time: {spent_time}\\n")

        await redis_group.increment_player_score(
            group_quiz_id=str(group_quiz.pk),
            user_id=user_id,
            is_correct=is_correct,
            spent_time=spent_time,
            username=username
        )
        
        with open("poll_debug.log", "a") as f:
            f.write(f"SUCCESS\\n")

    except Exception as e:
        with open("poll_debug.log", "a") as f:
            f.write(f"ERROR: {e}\\n{traceback.format_exc()}\\n")



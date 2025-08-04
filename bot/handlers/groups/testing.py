
import time
from aiogram import types
from aiogram.fsm.context import FSMContext

from quiz.models import GroupQuiz

from bot import utils
from bot.states import QuizState
from bot.utils.functions import get_text, generate_user_quiz_data
from .send_test import send_tests_by_recurse
from .common import animate_texts, delete_quiz_reply_markup


async def testing_send_tests_by_recurse(group_quiz: GroupQuiz, callback: types.CallbackQuery, state: FSMContext):
    language = group_quiz.language or "en"
    await delete_quiz_reply_markup(group_quiz.group_id, group_quiz.message_id, callback)
    message_id = await animate_texts(group_quiz.group_id, callback, language=language)

    await callback.bot.delete_message(chat_id=group_quiz.group_id, message_id=message_id)
    await state.set_state(QuizState.group_testing)

    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question', language)

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

    language = group_quiz.language or "en"
    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question', language)

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


async def testing_group_poll_answer_handler(poll_answer: types.PollAnswer):
    end_time = time.perf_counter()
    group_quiz = await utils.get_group_quiz_by_poll_id(poll_answer.poll_id)

    if not group_quiz:
        return

    if not group_quiz.is_answered:
        group_quiz.is_answered = True
        group_quiz.answers += 1

    players_data = group_quiz.data.get('players', {})
    user_id = str(poll_answer.user.id)
    if poll_answer.voter_chat:
        user_id = str(poll_answer.voter_chat.id)

    user_data = players_data.get(user_id, None)
    if poll_answer.user.username:
        username = "@" + poll_answer.user.username
    else:
        username = poll_answer.user.first_name

    if not user_data:
        user_data = {
            'corrects': 0,
            'wrongs': 0,
            'spent_time': 0,
            'username': username
        }

    if poll_answer.option_ids[0] == group_quiz.data.get('correct_option_id', 10):
        user_data['corrects'] += 1
    else:
        user_data['wrongs'] += 1

    user_data['spent_time'] += round(end_time - group_quiz.data.get('start_time', 0), 1)
    players_data[user_id] = user_data
    group_quiz.data['players'] = players_data
    await group_quiz.asave(update_fields=['data', 'is_answered', 'answers'])


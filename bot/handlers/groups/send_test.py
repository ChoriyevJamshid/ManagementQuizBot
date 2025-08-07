
import time
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext


from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text
from .statistics import send_statistics


async def send_tests_by_recurse(
        group_id: str,
        index: int,
        question_data: dict,
        poll_question: str,
        timer: int,
        callback: types.CallbackQuery,
        state: FSMContext
):
    total_questions = len(question_data)

    if index >= total_questions:
        return await send_statistics(group_id, callback.bot)

    group_quiz = await utils.get_group_quiz(group_id)
    if not group_quiz:
        return None

    language = group_quiz.language or "en"
    if index != 0 and not group_quiz.is_answered:
        group_quiz.skips += 1
        await group_quiz.asave(update_fields=['skips'])

    if group_quiz.is_answered:
        group_quiz.is_answered = False
        await group_quiz.asave(update_fields=['is_answered'])

    if group_quiz.skips == 2:
        group_quiz.skips = 0
        await group_quiz.asave(update_fields=['skips'])

        text = await get_text('group_noone_answer_to_questions', language)
        markup = await inline_kb.test_group_continue_markup(group_id, index, language)

        return await callback.bot.send_message(
            chat_id=group_id,
            text=text,
            reply_markup=markup,
        )

    question_text = (f"<b>[{index + 1}/{total_questions}]. {question_data[index]['question']}</b>\n\n"
                     f"<b>A)</b> {question_data[index]['options'][0]}\n\n"
                     f"<b>B)</b> {question_data[index]['options'][1]}\n\n"
                     f"<b>C)</b> {question_data[index]['options'][2]}\n\n"
                     f"<b>D)</b> {question_data[index]['options'][3]}\n\n")
    correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])

    await callback.bot.send_message(chat_id=group_quiz.group_id, text=question_text)
    poll = await callback.bot.send_poll(
        chat_id=group_quiz.group_id,
        question=poll_question,
        options=['A', 'B', 'C', 'D'],
        is_anonymous=False,
        type='quiz',
        correct_option_id=correct_option_id,
        open_period=timer,
        protect_content=True
    )

    group_quiz.poll_id = poll.poll.id
    group_quiz.index = index + 1
    group_quiz.data['start_time'] = time.perf_counter()
    group_quiz.data['correct_option_id'] = correct_option_id
    await group_quiz.asave(update_fields=['poll_id', 'index', 'data'])

    await asyncio.sleep(timer + 2)
    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=index + 1,
        question_data=question_data,
        poll_question=poll_question,
        timer=timer,
        callback=callback,
        state=state
    )


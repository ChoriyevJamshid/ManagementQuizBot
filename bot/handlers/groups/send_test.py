
import time
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext


from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text
from bot.utils import redis_group
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

    if index != 0 and not group_quiz.is_answered:
        group_quiz.skips += 1
        await group_quiz.asave(update_fields=['skips'])

    if group_quiz.is_answered:
        await type(group_quiz).objects.filter(pk=group_quiz.pk).aupdate(is_answered=False)
        group_quiz.is_answered = False

    if group_quiz.skips == 2:
        group_quiz.skips = 0
        await group_quiz.asave(update_fields=['skips'])

        text = await get_text('group_noone_answer_to_questions')
        markup = await inline_kb.test_group_continue_markup(group_id, index)

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
    await group_quiz.asave(update_fields=['poll_id', 'index'])

    # Save timing and correct answers directly to Redis for the answer handlers
    await redis_group.set_group_question_data(
        group_quiz_id=str(group_quiz.pk),
        correct_option_id=correct_option_id,
        start_time=time.perf_counter()
    )

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


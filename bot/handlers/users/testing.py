import asyncio
import time
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from quiz.choices import QuizStatus

from bot import utils
from bot.keyboards import inline_kb, reply_kb
from bot.states import QuizState
from bot.utils.functions import (
    get_text,
    generate_user_quiz_data,
    testing_animation
)
from bot.handlers.groups.common import check_quiz_part_owner


async def testing_stop_quiz_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(current_user_quiz=None)

    user = await utils.get_user(message.from_user)
    user_quiz = await utils.get_user_active_quiz(user.id)
    language = user.language if user.language else "en"

    if not user_quiz:
        text = await get_text("testing_not_active_quiz", language)
        await message.answer(text)
        return await state.clear()


    current_user_quiz = data.get("current_user_quiz", {})
    times = current_user_quiz.get('times', 0)
    minutes, seconds = times // 60, times % 60

    if not current_user_quiz:

        user_quiz.status = QuizStatus.CANCELED
        user_quiz.active = False
        user_quiz.save(update_fields=['status', 'active'])
        await state.set_state(QuizState.finished)

        text = await get_text("please_press_start", language)
        return message.answer(text)

    markup = await inline_kb.test_finished_markup(user_quiz.part.link, language)
    text = await get_text_with_or_without_minute(
        minutes, seconds, user_quiz.part.quiz.title, user_quiz.part.quantity, current_user_quiz, language)

    await message.answer(text=text, reply_markup=markup)
    await state.set_state(QuizState.finished)
    return await save_user_quiz(user.id, current_user_quiz, QuizStatus.CANCELED)


async def testing_link_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'
    data_solo = await utils.get_data_solo()

    title = await utils.get_exists_user_active_quiz(user.id)
    if title is not None:
        text = await get_text("testing_quiz_active_not_stopped", language, {
            "title": title
        })
        return await message.answer(text)


    link = message.text.split('_')[-1]
    if len(message.text.split(' ')) == 2:
        link = message.text.split(' ')[-1]

    quiz_part = await utils.get_quiz_part(link)
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    except Exception as e:
        pass

    if not quiz_part:
        text = await get_text('testing_quiz_part_not_found', language)
        return await message.answer(text)

    is_owner = await check_quiz_part_owner(
        quiz_part=quiz_part,
        user=user,
        message=message,
        language=quiz_part.quiz.owner.language or "en"
    )

    if not is_owner:
        return None




    players_count = await utils.get_user_quizzes_count(quiz_part.id)
    if players_count == 0:
        text = await get_text(
            'testing_quiz_part_info_not_answered', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.quiz.title),
            }
        )
    else:
        text = await get_text(
            'testing_quiz_part_info_answered', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.quiz.title),
                "users": str(players_count)
            }
        )
    markup = await inline_kb.   test_manage_markup(
        part_id=quiz_part.id,
        language=language,
        username=data_solo.username,
        link=quiz_part.link
    )
    await message.answer(text, reply_markup=markup)
    return await state.set_state(QuizState.quizzes)


async def testing_start_pressed_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    title = await utils.get_exists_user_active_quiz(user.id)
    if title is not None:
        text = await get_text("testing_quiz_active_not_stopped", language, {
            "title": title
        })
        await callback.message.answer(text)
        return await callback.answer()

    part_id = int(callback.data.split('_')[-1])
    quiz_part = await utils.get_quiz_part_by_id(part_id)

    text = await get_text(
        'testing_quiz_part_ready_info', language,
        {
            "from_i": str(quiz_part.from_i),
            "to_i": str(quiz_part.to_i),
            "quantity": str(quiz_part.quantity),
            "timer": str(quiz_part.quiz.timer),
            "title": str(quiz_part.quiz.title),
        }
    )
    markup = await inline_kb.test_start_markup(part_id, language)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def testing_ready_pressed_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(ready_message_id=None)

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    title = await utils.get_exists_user_active_quiz(user.id)
    if title is not None:
        text = await get_text("testing_quiz_active_not_stopped", language, {
            "title": title
        })
        return await callback.answer(text)

    part_id = int(callback.data.split('_')[-1])
    part = await utils.get_quiz_part_by_id(part_id)
    user_quiz = await utils.create_user_quiz(part.id, user.id)
    question_data = await generate_user_quiz_data(part)

    user_quiz.data = question_data
    user_quiz.save(update_fields=['data'])

    index = 0
    poll_question = await get_text('poll_question', language)
    question_text = (f"<b>{index + 1}. {question_data[index]['question']}</b>\n\n"
                     f"<b>A)</b> <i>{question_data[index]['options'][0]}</i>\n"
                     f"<b>B)</b> <i>{question_data[index]['options'][1]}</i>\n"
                     f"<b>C)</b> <i>{question_data[index]['options'][2]}</i>\n"
                     f"<b>D)</b> <i>{question_data[index]['options'][3]}</i>\n")
    correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])
    current_user_quiz = {
        'id': user_quiz.id,
        'title': user_quiz.part.quiz.title,
        'index': index,
        'correct_option_id': correct_option_id,
        "corrects": 0,
        "wrongs": 0,
        "skips": 0,
        "times": 0,
    }

    await testing_animation(callback, language)

    user_quiz = await utils.get_user_active_quiz(user.id)
    if not user_quiz:
        return

    await callback.message.answer(question_text)
    current_user_quiz["start_time"] = time.perf_counter()

    await state.update_data(current_user_quiz=current_user_quiz)
    await callback.message.answer_poll(
        question=poll_question,
        options=['A', 'B', 'C', 'D'],
        is_anonymous=False,
        type='quiz',
        correct_option_id=correct_option_id,
        open_period=part.quiz.timer,
        protect_content=True
    )
    await state.set_state(QuizState.testing)
    await asyncio.sleep(part.quiz.timer + 2)

    data = await state.get_data()
    current_user_quiz = data.get('current_user_quiz', {})

    if not current_user_quiz:
        return

    user_quiz_id = int(current_user_quiz.get('id', 0))
    if user_quiz_id != user_quiz.id:
        return

    new_index = int(current_user_quiz.get('index', 0))
    if new_index > index:
        return

    await testing_send_skipped_question_function(user, callback.bot, state)


async def testing_poll_answer_handler(poll_answer: types.PollAnswer, state: FSMContext):

    end_time = time.perf_counter()
    data = await state.get_data()
    user = await utils.get_user(poll_answer.user)
    language = user.language if user.language else 'en'

    current_user_quiz = data.get('current_user_quiz', {})

    if not current_user_quiz:
        return

    index = int(current_user_quiz.get('index', 0)) + 1
    correct_option_id = int(current_user_quiz.get('correct_option_id', 0))
    start_time = current_user_quiz.get('start_time')
    chosen_option_id = int(poll_answer.option_ids[0])

    user_quiz = await utils.get_user_active_quiz(user.id)

    if not user_quiz:
        return

    question_data = user_quiz.data
    current_user_quiz["times"] += int(end_time - start_time)
    if correct_option_id == chosen_option_id:
        current_user_quiz['corrects'] += 1
    else:
        current_user_quiz['wrongs'] += 1

    if index < user_quiz.part.quantity:

        poll_question = await get_text('poll_question', language)
        question_text = (f"<b>{index + 1}. {question_data[index]['question']}</b>\n\n"
                         f"<b>A)</b> <i>{question_data[index]['options'][0]}</i>\n"
                         f"<b>B)</b> <i>{question_data[index]['options'][1]}</i>\n"
                         f"<b>C)</b> <i>{question_data[index]['options'][2]}</i>\n"
                         f"<b>D)</b> <i>{question_data[index]['options'][3]}</i>\n")
        correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])
        current_user_quiz['index'] = index
        current_user_quiz['correct_option_id'] = correct_option_id
        current_user_quiz['start_time'] = time.perf_counter()

        await state.update_data(current_user_quiz=current_user_quiz)
        await poll_answer.bot.send_message(
            chat_id=poll_answer.user.id,
            text=question_text
        )
        await poll_answer.bot.send_poll(
            chat_id=poll_answer.user.id,
            question=poll_question,
            options=['A', 'B', 'C', 'D'],
            is_anonymous=False,
            type='quiz',
            correct_option_id=correct_option_id,
            open_period=user_quiz.part.quiz.timer,
            protect_content=True
        )
        await asyncio.sleep(user_quiz.part.quiz.timer + 2)

        data = await state.get_data()
        current_user_quiz = data.get('current_user_quiz', {})

        if not current_user_quiz:
            return

        user_quiz_id = int(current_user_quiz.get('id', 0))
        if user_quiz_id != user_quiz.id:
            return

        new_index = int(current_user_quiz.get('index', 0))
        if new_index > index:
            return

        await testing_send_skipped_question_function(user, poll_answer.bot, state)

    else:
        await state.update_data(current_user_quiz=None)

        times = current_user_quiz.get('times', 0)
        minutes, seconds = times // 60, times % 60

        markup = await inline_kb.test_finished_markup(user_quiz.part.link, language)
        text = await get_text_with_or_without_minute(
            minutes, seconds, user_quiz.part.quiz.title, user_quiz.part.quantity, current_user_quiz, language)

        await poll_answer.bot.send_message(
            chat_id=poll_answer.user.id,
            text=text,
            reply_markup=markup
        )
        await state.set_state(QuizState.finished)
        await save_user_quiz(user.id, current_user_quiz, QuizStatus.FINISHED)


async def testing_continue_quiz_handler(callback: types.CallbackQuery, state: FSMContext):

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    user_quiz = await utils.get_user_active_quiz(user.id)

    if not user_quiz:
        return

    current_user_quiz = user_quiz.current_data
    question_data = user_quiz.data

    index = int(current_user_quiz.get('index', 0)) + 1
    if index < user_quiz.part.quantity:

        poll_question = await get_text('poll_question', language)
        question_text = (f"<b>{index + 1}. {question_data[index]['question']}</b>\n\n"
                         f"<b>A)</b> <i>{question_data[index]['options'][0]}</i>\n"
                         f"<b>B)</b> <i>{question_data[index]['options'][1]}</i>\n"
                         f"<b>C)</b> <i>{question_data[index]['options'][2]}</i>\n"
                         f"<b>D)</b> <i>{question_data[index]['options'][3]}</i>\n")
        correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])
        current_user_quiz['index'] = index
        current_user_quiz['correct_option_id'] = correct_option_id
        current_user_quiz['start_time'] = time.perf_counter()

        await callback.message.delete_reply_markup()
        await state.update_data(current_user_quiz=current_user_quiz)
        await callback.message.answer(text=question_text)
        await callback.message.answer_poll(
            question=poll_question,
            options=['A', 'B', 'C', 'D'],
            is_anonymous=False,
            type='quiz',
            correct_option_id=correct_option_id,
            open_period=user_quiz.part.quiz.timer,
            protect_content=True
        )

        await asyncio.sleep(user_quiz.part.quiz.timer + 2)

        data = await state.get_data()
        current_user_quiz = data.get('current_user_quiz', {})

        if not current_user_quiz:
            return

        user_quiz_id = int(current_user_quiz.get('id', 0))
        if user_quiz_id != user_quiz.id:
            return

        new_index = int(current_user_quiz.get('index', 0))
        if new_index > index:
            return

        await testing_send_skipped_question_function(user, callback.bot, state)

    else:
        await state.update_data(current_user_quiz=None)

        times = current_user_quiz.get('times', 0)
        minutes, seconds = times // 60, times % 60

        markup = await inline_kb.test_finished_markup(user_quiz.part.link, language)
        text = await get_text_with_or_without_minute(
            minutes, seconds, user_quiz.part.quiz.title, user_quiz.part.quantity, current_user_quiz, language)

        await callback.message.answer(text=text, reply_markup=markup)
        await state.set_state(QuizState.finished)
        await save_user_quiz(user.id, current_user_quiz, QuizStatus.FINISHED)


async def testing_try_retry_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    title = await utils.get_exists_user_active_quiz(user.id)
    if title is not None:
        text = await get_text("testing_quiz_active_not_stopped", language, {
            "title": title
        })
        await callback.message.answer(text)
        return

    link = callback.data.split('_')[-1]
    quiz_part = await utils.get_quiz_part(link)

    if not quiz_part:
        text = await get_text('testing_quiz_part_not_found', language)
        await callback.message.answer(text)
        return

    if quiz_part.quiz.owner_id != user.id and quiz_part.privacy is False:
        text = await get_text(
            'testing_quiz_part_not_allowed_by_owner', language,
            {
                'title': quiz_part.quiz.title,
                'owner': quiz_part.quiz.owner.username \
                    if quiz_part.quiz.owner.username \
                    else quiz_part.quiz.owner.first_name,
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
            }
        )
        return await callback.message.answer(text)

    players_count = await utils.get_user_quizzes_count(quiz_part.id)

    if players_count == 0:
        text = await get_text(
            'testing_quiz_part_info_not_answered', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.quiz.title),
            }
        )
    else:
        text = await get_text(
            'testing_quiz_part_info_answered', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.quiz.title),
                "users": str(players_count)
            }
        )


    if data.get('ready_message_id', None) is not None:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=data['ready_message_id'],
            reply_markup=None
        )
    markup = await inline_kb.test_start_markup(quiz_part.id, language)
    message = await callback.message.answer(text, reply_markup=markup)
    await state.update_data(ready_message_id=message.message_id)


async def testing_send_skipped_question_function(user, bot: Bot, state: FSMContext):
    data = await state.get_data()
    language = user.language if user.language else 'en'
    current_user_quiz = data.get('current_user_quiz', {})
    index = int(current_user_quiz.get('index', 0)) + 1

    user_quiz = await utils.get_user_active_quiz(user.id)

    if not user_quiz:
        return

    question_data = user_quiz.data
    current_user_quiz["times"] += user_quiz.part.quiz.timer
    current_user_quiz['skips'] += 1

    if index < user_quiz.part.quantity:

        if current_user_quiz["skips"] % 2 == 0:
            text = await get_text("testing_user_stops_answering", language)
            markup = await inline_kb.test_continue_markup(language)
            user_quiz.current_data = current_user_quiz
            user_quiz.save(update_fields=['current_data'])

            await state.clear()
            await bot.send_message(
                chat_id=user.chat_id,
                text=text,
                reply_markup=markup,
            )
            await state.set_state(QuizState.testing)
            return

        poll_question = await get_text('poll_question', language)
        question_text = (f"<b>{index + 1}. {question_data[index]['question']}</b>\n\n"
                         f"<b>A)</b> <i>{question_data[index]['options'][0]}</i>\n"
                         f"<b>B)</b> <i>{question_data[index]['options'][1]}</i>\n"
                         f"<b>C)</b> <i>{question_data[index]['options'][2]}</i>\n"
                         f"<b>D)</b> <i>{question_data[index]['options'][3]}</i>\n")
        correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])
        current_user_quiz['index'] = index
        current_user_quiz['correct_option_id'] = correct_option_id
        current_user_quiz['start_time'] = time.perf_counter()

        await state.update_data(current_user_quiz=current_user_quiz)
        await bot.send_message(
            chat_id=user.chat_id,
            text=question_text
        )
        await bot.send_poll(
            chat_id=user.chat_id,
            question=poll_question,
            options=['A', 'B', 'C', 'D'],
            is_anonymous=False,
            type='quiz',
            correct_option_id=correct_option_id,
            open_period=user_quiz.part.quiz.timer,
            protect_content=True
        )

        await asyncio.sleep(user_quiz.part.quiz.timer + 2)

        data = await state.get_data()
        current_user_quiz = data.get('current_user_quiz', {})

        if not current_user_quiz:
            return

        user_quiz_id = int(current_user_quiz.get('id', 0))
        if user_quiz_id != user_quiz.id:
            return

        new_index = int(current_user_quiz.get('index', 0))
        if new_index > index:
            return

        await testing_send_skipped_question_function(user, bot, state)

    else:
        await state.update_data(current_user_quiz=None)

        times = current_user_quiz.get('times', 0)
        minutes, seconds = times // 60, times % 60

        markup = await inline_kb.test_finished_markup(user_quiz.part.link, language)
        text = await get_text_with_or_without_minute(
            minutes, seconds, user_quiz.part.quiz.title, user_quiz.part.quantity, current_user_quiz, language)
        await bot.send_message(
            chat_id=user.chat_id,
            text=text,
            reply_markup=markup
        )
        await state.set_state(QuizState.finished)
        await save_user_quiz(user.id, current_user_quiz, QuizStatus.FINISHED)


async def save_user_quiz(user_id: int, data: dict, quiz_status):
    user_quiz = await utils.get_user_active_quiz(user_id)
    user_quiz.corrects = data['corrects']
    user_quiz.wrongs = data['wrongs']
    user_quiz.skips = data['skips']
    user_quiz.times = data['times']
    user_quiz.current_data = {}
    user_quiz.status = quiz_status
    user_quiz.active = False
    user_quiz.save()


async def get_text_with_or_without_minute(
        minutes: int,
        seconds: int,
        title: str,
        quantity: int,
        current_user_quiz,
        language
):
    qnt = current_user_quiz.get('corrects', 0) + current_user_quiz.get('wrongs', 0) + current_user_quiz.get('skips', 0)
    if minutes > 0:
        text = await get_text("testing_user_finished_quiz_with_minute", language, parameters={
            "title": title,
            "quantity": str(qnt),
            "corrects": str(current_user_quiz['corrects']),
            "wrongs": str(current_user_quiz['wrongs']),
            "skips": str(current_user_quiz['skips']),
            "seconds": str(seconds),
            "minutes": str(minutes),
        })
    else:
        text = await get_text("testing_user_finished_quiz_without_minute", language, parameters={
            "title": title,
            "quantity": str(qnt),
            "corrects": str(current_user_quiz['corrects']),
            "wrongs": str(current_user_quiz['wrongs']),
            "skips": str(current_user_quiz['skips']),
            "seconds": str(seconds),
        })
    return text

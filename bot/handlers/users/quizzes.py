from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb, reply_kb
from bot.states import *
from bot.utils.functions import *


async def quiz_list_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    quiz_data = {}
    page_number = 1
    paginate_by = 10

    quizzes = await utils.get_user_quizzes(user.id)

    if not quizzes:
        text = await get_text("quiz_list_user_not_quizzes", language)
        await callback.answer(text)
        return

    from_i = (page_number - 1) * paginate_by
    to_i = page_number * paginate_by if len(quizzes) > page_number * paginate_by else len(quizzes)
    total_pages = len(quizzes) // paginate_by if not len(quizzes) % paginate_by else len(quizzes) // paginate_by + 1

    quizzes = quizzes[from_i:to_i]
    text = await get_text('quiz_list_user_quizzes', language)
    text += "\n"
    for index, quiz in enumerate(quizzes, start=1):
        text += f"\n<b>Quiz №{from_i + index}</b>. <i>{quiz['title']}</i>"
        quiz_data[from_i + index] = quiz['id']

    await state.update_data({
        "current_page": page_number,
        "total_pages": total_pages,
    })
    await callback.message.edit_text(
        text=text, reply_markup=await inline_kb.get_quizzes_markup(quiz_data, state, language)
    )
    await callback.answer()
    await state.set_state(QuizState.quizzes)


async def quiz_list_paginate_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    cd = int(callback.data.split('_')[-1])
    current_page = int(data.get('current_page', 0))

    if cd == current_page:
        return await callback.answer()

    quiz_data = {}
    paginate_by = 10
    page_number = cd
    quizzes = await utils.get_user_quizzes(user.id)

    from_i = (page_number - 1) * paginate_by
    to_i = page_number * paginate_by if len(quizzes) > page_number * paginate_by else len(quizzes)
    total_pages = len(quizzes) // paginate_by if not len(quizzes) % paginate_by else len(quizzes) // paginate_by + 1

    quizzes = quizzes[from_i:to_i]
    text = await get_text('quiz_list_user_quizzes', language)
    text += "\n"
    for index, quiz in enumerate(quizzes, start=1):
        text += f"\n<b>Quiz №{from_i + index}</b>. <i>{quiz['title']}</i>"
        quiz_data[from_i + index] = quiz['id']

    await state.update_data({
        "current_page": page_number,
        "total_pages": total_pages,
    })
    await callback.message.edit_text(
        text=text, reply_markup=await inline_kb.get_quizzes_markup(quiz_data, state, language)
    )
    await callback.answer()


async def quiz_list_detail_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    quiz_id = int(callback.data.split('_')[-1])
    quiz = await utils.get_quiz_by_id(quiz_id)
    quiz_parts = await utils.get_quiz_parts(quiz_id)

    text = await get_text('quiz_list_detail_quiz_parts', language)
    markup = await inline_kb.quiz_detail_markup(quiz, language)
    text += "\n"
    for index, quiz_part in enumerate(quiz_parts, start=1):
        text += f"\n<b>{index}. [{quiz_part.from_i} - {quiz_part.to_i}]</b> 👉 /quiz_{quiz_part.link}"

    await callback.message.edit_text(text=text, reply_markup=markup)
    await callback.answer()


async def quiz_list_edit_timer_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    quiz_id = int(callback.data.split('_')[-1])

    text = await get_text('edit_quiz_timer', language)
    markup = await reply_kb.quiz_timers_markup(language, without_back=True)

    await state.update_data(update_quiz_id=quiz_id)
    await callback.message.delete_reply_markup()
    await callback.message.answer(text, reply_markup=markup)
    await state.set_state(QuizState.update_timer)
    await callback.answer()


async def quiz_list_timer_edit_success_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else "en"

    texts = await get_texts(('second', 'minute', 'back_text'), language)
    timers = (
        f"10 {texts['second']}",
        f"15 {texts['second']}",
        f"20 {texts['second']}",
        f"25 {texts['second']}",
        f"30 {texts['second']}",
        f"45 {texts['second']}",
        f"1 {texts['minute']}",
        f"1 {texts['minute']} 15 {texts['second']}",
        f"1 {texts['minute']} 30 {texts['second']}",
        f"1 {texts['minute']} 45 {texts['second']}",
        f"2 {texts['minute']}",
        '/cancelTimer'
    )

    if message.text not in timers:
        text = await get_text('create_quiz_timer_not_allowed_timer', language)
        await message.answer(text)
        return

    quiz_id = int(data.get('update_quiz_id', 0))
    quiz = await utils.get_quiz_by_id(quiz_id)

    if not quiz:
        text = await get_text('quiz_list_quiz_not_found', language)
        await message.answer(text)
        return

    if message.text != '/cancelTimer':

        __ = message.text.split(' ')
        timer = 0
        for _ in __:
            if _.isdigit():
                timer += int(_) if int(_) >= 10 else int(_) * 60

        quiz.timer = timer
        quiz.save(update_fields=['timer'])

    texts = await get_texts((
        'quiz_list_timer_edit_success', 'quiz_list_detail_quiz_parts'
    ), language)

    text = texts['quiz_list_detail_quiz_parts']
    markup = await inline_kb.quiz_detail_markup(quiz, language)
    text += "\n"

    quiz_parts = await utils.get_quiz_parts(quiz_id)
    for index, quiz_part in enumerate(quiz_parts, start=1):
        text += f"\n<b>{index}. [{quiz_part.from_i} - {quiz_part.to_i}]</b> 👉 /quiz_{quiz_part.link}"

    await message.answer(texts['quiz_list_timer_edit_success'], reply_markup=await reply_kb.remove_kb())
    await message.answer(text=text, reply_markup=markup)
    await state.set_state(QuizState.quizzes)


async def quiz_list_edit_privacy_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    quiz_id = int(callback.data.split('_')[-1])
    quiz = await utils.get_quiz_values(quiz_id, ('id', 'title', 'privacy'))

    if not quiz:
        text = await get_text('quiz_not_found', language)
        return await callback.answer(text)

    texts = await get_texts(('turn_off', 'turn_on', 'turning_off', 'turning_on'), language)
    _privacy = "🔒" if quiz.get("privacy") is True else "🔐"
    ptext = texts['turn_off'] if quiz.get("privacy") is True else texts['turn_on']

    text = await get_text('quiz_list_edit_privacy', language, {
        'title': quiz.get('title', ''),
        "privacy": _privacy,
        "ptext": ptext
    })
    markup = await inline_kb.quiz_detail_edit_privacy_markup(quiz, texts)

    await callback.message.edit_text(text=text, reply_markup=markup)
    await state.set_state(QuizState.update_privacy)
    await callback.answer()


async def quiz_list_change_privacy_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    _, is_privacy, quiz_id = callback.data.split('_')

    quiz = await utils.get_quiz_by_id(int(quiz_id))

    if not quiz:
        text = await get_text('quiz_not_found', language)
        return await callback.answer(text)

    if int(is_privacy) == 0:
        _text = await get_text("quiz_detail_not_changed_privacy", language, {
            'title': quiz.title
        })

    elif int(is_privacy) == 1:
        _text = await get_text("quiz_detail_changed_privacy", language, {
            'title': quiz.title
        })
        quiz.privacy = not quiz.privacy
        quiz.save(update_fields=['privacy'])
    else:
        _text = ''

    quiz_parts = await utils.get_quiz_parts(quiz.id)

    text = await get_text('quiz_list_detail_quiz_parts', language)
    markup = await inline_kb.quiz_detail_markup(quiz, language)
    text += "\n"
    for index, quiz_part in enumerate(quiz_parts, start=1):
        text += f"\n<b>{index}. [{quiz_part.from_i} - {quiz_part.to_i}]</b> 👉 /quiz_{quiz_part.link}"

    await callback.message.edit_text(text=text, reply_markup=markup)
    await callback.answer(_text)
    await state.set_state(QuizState.quizzes)


async def quiz_list_back_to_main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else "en"

    markup = await inline_kb.main_menu_markup(user.language)
    text = await get_text('main_menu', language)
    await callback.message.edit_text(text, reply_markup=markup)
    await state.clear()
    await state.set_state(MainState.main_menu)
    await state.update_data(markup_message_id=callback.message.message_id)

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.states import MainState
from bot.keyboards import inline_kb, reply_kb
from bot.utils.functions import get_text, get_texts


async def categories_handler(callback: types.CallbackQuery, state: FSMContext):

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    categories = await utils.get_categories()
    if not categories:
        text = await get_text('categories_not_found', language)
        return await callback.answer(text, show_alert=True)

    text = await get_text('categories_list_text', language)
    markup = await inline_kb.get_categories_markup(categories, language)

    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(MainState.categories)
    await callback.answer()


async def categories_detail_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    _, category_title, category_id = callback.data.split('_')
    quizzes = await utils.get_quizzes_by_category_id(category_id=category_id)

    if not quizzes:
        text = await get_text('categories_category_not_quizzes', language, {
            'title': category_title
        })
        return await callback.answer(text)

    paginate_by = 20
    page_number = 1
    total_pages = len(quizzes) // paginate_by if not len(quizzes) % paginate_by else len(quizzes) // paginate_by + 1

    text = await get_text('categories_detail_text', language, {
        'category': category_title,
    })
    text += "\n"

    quiz_ids = []
    quizzes = quizzes[:paginate_by]
    for index, quiz in enumerate(quizzes, start=1):
        text += f"\n<b>Quiz #{index}:</b> <i>{quiz.title}</i>"
        quiz_ids.append(quiz.id)

    markup = await inline_kb.categories_detail_markup(quiz_ids, total_pages, page_number, language)
    await state.update_data({
        "cat_page_number": page_number,
        "cat_id": category_id,
        "cat_title": category_title,
    })
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=markup)


async def categories_paginate_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    page_number = int(callback.data.split('_')[-1])

    if page_number == int(data.get('cat_page_number', 1)):
        return await callback.answer()

    category_id = data.get('cat_id', '')
    category_title = data.get('cat_title', '')
    quizzes = await utils.get_quizzes_by_category_id(category_id=category_id)

    if not quizzes:
        return await callback.answer()

    paginate_by = 20
    total_pages = len(quizzes) // paginate_by if not len(quizzes) % paginate_by else len(quizzes) // paginate_by + 1

    from_i = (page_number - 1) * paginate_by
    to_i = page_number * paginate_by if page_number * paginate_by < len(quizzes) else len(quizzes)

    text = await get_text('categories_detail_text', language, {
        'category': category_title,
    })
    text += "\n"

    quiz_ids = []
    quizzes = quizzes[from_i:to_i]
    for index, quiz in enumerate(quizzes, start=1):
        text += f"\n<b>Quiz #{index}:</b> <i>{quiz.title}</i>"
        quiz_ids.append(quiz.id)

    markup = await inline_kb.categories_detail_markup(quiz_ids, total_pages, page_number, language)
    await state.update_data({
        "cat_page_number": page_number,
        "cat_title": category_title,
    })
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=markup)


async def categories_detail_quiz_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    quiz_id = int(callback.data.split('_')[-1])

    quiz = await utils.get_quiz_by_id(quiz_id)
    quiz_parts = await utils.get_quiz_parts(quiz_id)

    text = await get_text('categories_detail_quiz_parts_text', language, {
        "title": quiz.title,
    })
    markup = await inline_kb.categories_quiz_parts_markup(
        quiz_parts,
        quiz.category.title,
        quiz.category.id,
        language)

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def categories_back_to_quizzes_handler(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    _, category_title, category_id = callback.data.split('_')
    quizzes = await utils.get_quizzes_by_category_id(category_id=category_id)

    if not quizzes:
        return await callback.answer()

    paginate_by = 20
    page_number = data.get("cat_page_number", 1)
    total_pages = len(quizzes) // paginate_by if not len(quizzes) % paginate_by else len(quizzes) // paginate_by + 1

    from_i = (page_number - 1) * paginate_by
    to_i = page_number * paginate_by if page_number * paginate_by < len(quizzes) else len(quizzes)

    text = await get_text('categories_detail_text', language, {
        'category': category_title,
    })
    text += "\n"

    quiz_ids = []
    quizzes = quizzes[from_i:to_i]
    for index, quiz in enumerate(quizzes, start=1):
        text += f"\n<b>Quiz #{index}:</b> <i>{quiz.title}</i>"
        quiz_ids.append(quiz.id)

    markup = await inline_kb.categories_detail_markup(quiz_ids, total_pages, page_number, language)
    await state.update_data({
        "cat_page_number": page_number,
        "cat_title": category_title,
    })
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=markup)



async def categories_detail_quiz_part_handler(callback: types.CallbackQuery, state: FSMContext):

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    link = callback.data.split('_')[-1]
    quiz_part = await utils.get_quiz_part(link)

    if not quiz_part:
        text = await get_text('testing_quiz_part_not_found', language)
        return await callback.answer(text)

    players_count = await utils.get_user_quizzes_count(quiz_part.id)
    data_solo = await utils.get_data_solo()

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
    markup = await inline_kb.test_manage_markup(
        part_id=quiz_part.id,
        language=language,
        username=data_solo.username,
        link=quiz_part.link
    )
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


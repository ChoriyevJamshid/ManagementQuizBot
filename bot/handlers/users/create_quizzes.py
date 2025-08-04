import os
from aiogram import types
from aiogram.fsm.context import FSMContext

from django.conf import settings
from common.models import TelegramProfile
from quiz import models as quiz_models

from bot import utils
from bot import states
from bot.keyboards import reply_kb
from bot.utils.functions import (
    get_text,
    get_texts,
    get_data_from_document,
    get_data_from_xlsx,
    get_data_from_txt,
    generate_unique_link
)

async def create_quiz_handler(callback: types.CallbackQuery, state: FSMContext):
    """
    This handler must not register
    """

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    text = await get_text('create_quiz_title', language)
    await callback.message.edit_text(text)
    await callback.answer()
    await state.set_state(states.CreateQuizState.title)


async def create_quiz_get_title_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_title', language)
        return await message.answer(text)

    if message.text.startswith("/"):
        text = await get_text('create_quiz_not_allowed_title', language)
        await message.answer(text)
        return await message.delete()

    text = await get_text('create_quiz_category', language)
    markup = await reply_kb.quiz_category_markup(language, state)
    await state.update_data(quiz_title=message.text)
    await message.answer(text, reply_markup=markup)
    return await state.set_state(states.CreateQuizState.category)


async def create_quiz_get_category_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_category', language)
        return await message.answer(text)

    if message.text.startswith('🔙'):
        text = await get_text('create_quiz_title', language)
        markup = await reply_kb.remove_kb()
        await message.answer(text, reply_markup=markup)
        await state.set_state(states.CreateQuizState.title)
        return

    if message.text.startswith("#"):
        iterator, category_title = message.text.split('. ')
        iterator = iterator.replace('#', '')

        await state.update_data(
            iterator=iterator,
            category_title=category_title,
        )

    elif message.text != "/skipCategory":
        categories = await utils.get_categories()
        texts = await get_texts(categories.values_list('title', flat=True), language)

        if message.text not in texts.values():
            text = await get_text('create_quiz_category_not_found', language)
            return await message.answer(text)
        await state.update_data(
            quiz_category_id=categories.filter(
                title=data.get('categories', {})[message.text]
            ).first().id,
            quiz_category_title=categories.filter(
                title=data.get('categories', {})[message.text]
            ).first().title,
        )

    else:
        pass

    text = await get_text('create_quiz_file', language)
    markup = await reply_kb.back_markup(language)

    await message.answer(text, reply_markup=markup)
    return await state.set_state(states.CreateQuizState.file)


async def create_quiz_get_file_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'


    if message.text:
        if message.text.startswith('🔙'):
            text = await get_text('create_quiz_category', language)
            markup = await reply_kb.quiz_category_markup(language, state)
            await message.answer(text, reply_markup=markup)
            return await state.set_state(states.CreateQuizState.category)
        return await message.delete()

    if not message.document:
        text = await get_text('create_quiz_file_not_document', language)
        markup = await reply_kb.back_markup(language)
        return await message.answer(text, reply_markup=markup)


    if message.document.file_name.split('.')[-1] not in ('docx', 'xlsx', 'txt'):
        text = await get_text('create_quiz_file_not_correct_extension', language)
        markup = await reply_kb.back_markup(language)
        return await message.answer(text, reply_markup=markup)


    question_data = []
    file_name, file_formate = await download_file(message.bot, message.document.file_id)
    if file_formate == 'docx':
        question_data = await get_data_from_document(f"{settings.BASE_DIR}/media/{file_name}")

    elif file_formate == 'xlsx':
        question_data = await get_data_from_xlsx(f"{settings.BASE_DIR}/media/{file_name}")

    elif file_formate == 'txt':
        question_data = await get_data_from_txt(f"{settings.BASE_DIR}/media/{file_name}")


    if not question_data:
        text = await get_text('create_quiz_file_not_questions', language)
        return await message.answer(text)

    text = await get_text('create_quiz_timer', language)
    markup = await reply_kb.quiz_timers_markup(language)
    await message.answer(text, reply_markup=markup)
    await state.update_data(
        quiz_file_id=message.document.file_id,
        quiz_question_data=question_data,
        quiz_quantity=len(question_data),
    )
    return await state.set_state(states.CreateQuizState.timer)


async def create_quiz_get_timer_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_timer', language)
        return await message.answer(text)

    if message.text.startswith('🔙'):
        text = await get_text('create_quiz_file', language)
        markup = await reply_kb.back_markup(language)
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.file)


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
    )

    if message.text not in timers:
        text = await get_text('create_quiz_timer_not_allowed_timer', language)
        return await message.answer(text)


    __ = message.text.split(' ')
    timer = 0
    for _ in __:
        if _.isdigit():
            timer += int(_) if int(_) >= 10 else int(_) * 60

    category = data.get('category_title', None)
    text = await get_text(
        'create_quiz_check_before_save', language,
        parameters={
            'title': data.get('quiz_title', ''),
            'timer': message.text,
            'category': category if category else '🚫',
            'quantity': str(data.get('quiz_quantity', '')),
        }
    )
    markup = await reply_kb.quiz_save_markup(language)
    await state.update_data(quiz_timer=timer)
    await message.answer(text, reply_markup=markup)
    return await state.set_state(states.CreateQuizState.save)


async def create_quiz_save_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if message.content_type != types.ContentType.TEXT:
        markup = await reply_kb.quiz_save_markup(language)
        text = await get_text('use_below_buttons_text', language)
        return await message.answer(text, reply_markup=markup)

    if message.text and message.text.startswith('🔙'):
        text = await get_text('create_quiz_timer', language)
        markup = await reply_kb.quiz_timers_markup(language)
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.timer)

    if message.text and not message.text.startswith('📂'):
        return await message.delete()

    text = await get_text('create_quiz_success', language)
    markup = await reply_kb.remove_kb()

    await message.answer(text, reply_markup=markup)
    await state.clear()
    return await create_quiz(message, data, user)


async def download_file(bot, file_id: str):
    os.makedirs(f"{settings.BASE_DIR}/media", exist_ok=True)
    _file_names = os.listdir(f"{settings.BASE_DIR}/media")

    # new_file_name = 1
    # if len(_file_names) > 0:

    file = await bot.get_file(file_id)
    file_formate = file.file_path.split('.')[-1]
    new_file = f"{file.file_id}.{file_formate}"
    await bot.download_file(file.file_path, f"media/{new_file}")

    return new_file, file_formate


async def create_quiz(message: types.Message, data: dict, user: TelegramProfile):
    """
    Not handler
    """

    title = data.get('quiz_title', '')
    timer = data.get('quiz_timer', 0)
    iterator = data.get('iterator', None)
    file_id = data.get('quiz_file_id', '')
    question_data = data.get('quiz_question_data', [])

    by_ques = 25
    total_ques = len(question_data)
    total_parts = total_ques // by_ques if not total_ques % by_ques else total_ques // by_ques + 1
    category = await utils.get_category_by_iterator(iterator)

    new_quiz = quiz_models.Quiz.objects.create(
        owner_id=user.id,
        title=title[:127],
        file_id=file_id,
        category=category,
        timer=timer,
        quantity=total_ques,

    )

    for i in range(total_parts):
        while True:
            link = await generate_unique_link()
            if not quiz_models.QuizPart.objects.filter(link=link).exists():
                break

        from_i = i * by_ques + 1
        to_i = (i + 1) * by_ques if (i + 1) * by_ques <= total_ques else total_ques
        quantity = to_i - from_i + 1

        part_title = f"№0{i + 1}" if (i + 1) < 10 else f"№{i + 1}"
        new_part = quiz_models.QuizPart.objects.create(
            quiz_id=new_quiz.id,
            link=link,
            from_i=from_i,
            to_i=to_i,
            quantity=quantity,
            title=f"{title[:127]} {part_title}"
        )

        for j in range(quantity):
            question = quiz_models.Question.objects.create(
                part_id=new_part.id,
                text=question_data[i * by_ques + j]['question'],
            )

            options = []
            for k in range(4):
                is_correct = False
                if not k:
                    is_correct = True
                options.append(
                    quiz_models.Option(
                        question_id=question.id,
                        text=question_data[i * by_ques + j]['options'][k],
                        is_correct=is_correct,
                    )
                )
            quiz_models.Option.objects.bulk_create(options)

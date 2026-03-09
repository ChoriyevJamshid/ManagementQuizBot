from pathlib import Path
from random import choice
from string import ascii_letters, digits

from aiogram import types
from aiogram.fsm.context import FSMContext

from django.conf import settings
from django.db import IntegrityError, transaction
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
)


ALLOWED_EXTENSIONS = {'docx', 'xlsx', 'txt'}
PART_QUESTION_OPTIONS = {20, 25, 30, 35}


def _normalize_text(value: str) -> str:
    return ' '.join(str(value).strip().split()).casefold()


def _prepare_question_data(raw_questions: list[dict]) -> list[dict]:
    prepared = []
    for row in raw_questions:
        question = str(row.get('question', '')).strip()[:512]
        correct_answer = str(row.get('correct_answer', '')).strip()[:512]
        options_raw = row.get('options') or []

        cleaned_options = []
        for option in options_raw:
            option_text = str(option).strip()[:512]
            if option_text:
                cleaned_options.append(option_text)

        if not question or len(cleaned_options) < 4:
            continue

        correct_norm = _normalize_text(correct_answer)
        correct_in_options = next(
            (option for option in cleaned_options if _normalize_text(option) == correct_norm),
            None,
        )

        if correct_in_options is None:
            continue

        options = cleaned_options[:4]
        if correct_in_options not in options:
            options = cleaned_options[:3] + [correct_in_options]

        prepared.append(
            {
                'question': question,
                'correct_answer': correct_in_options,
                'options': options,
            }
        )

    return prepared


def _parse_timer_seconds(timer_text: str) -> int:
    timer = 0
    for value in timer_text.split(' '):
        if value.isdigit():
            timer += int(value) if int(value) >= 10 else int(value) * 60
    return timer


def _generate_unique_link(length: int = 8) -> str:
    symbols = ascii_letters + digits
    return ''.join(choice(symbols) for _ in range(length))

async def create_quiz_handler(callback: types.CallbackQuery, state: FSMContext):
    """
    This handler must not register
    """

    text = await get_text('create_quiz_title')
    await callback.message.edit_text(text)
    await callback.answer()
    await state.set_state(states.CreateQuizState.title)


async def create_quiz_get_title_handler(message: types.Message, state: FSMContext):
    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_title')
        return await message.answer(text)

    if message.text.startswith("/"):
        text = await get_text('create_quiz_not_allowed_title')
        await message.answer(text)
        return await message.delete()

    text = await get_text('create_quiz_file')
    markup = await reply_kb.back_markup()
    await state.update_data(quiz_title=message.text)
    await message.answer(text, reply_markup=markup)
    return await state.set_state(states.CreateQuizState.file)





async def create_quiz_get_file_handler(message: types.Message, state: FSMContext):
    if message.text:
        if message.text.startswith('🔙'):
            text = await get_text('create_quiz_title')
            markup = await reply_kb.remove_kb()
            await message.answer(text, reply_markup=markup)
            return await state.set_state(states.CreateQuizState.title)
        return await message.delete()

    if not message.document:
        text = await get_text('create_quiz_file_not_document')
        markup = await reply_kb.back_markup()
        return await message.answer(text, reply_markup=markup)


    extension = Path(message.document.file_name or '').suffix.lower().lstrip('.')
    if extension not in ALLOWED_EXTENSIONS:
        text = await get_text('create_quiz_file_not_correct_extension')
        markup = await reply_kb.back_markup()
        return await message.answer(text, reply_markup=markup)

    try:
        file_path, file_format = await download_file(message.bot, message.document.file_id)
        if file_format == 'docx':
            raw_questions = await get_data_from_document(str(file_path))
        elif file_format == 'xlsx':
            raw_questions = await get_data_from_xlsx(str(file_path))
        else:
            raw_questions = await get_data_from_txt(str(file_path))
    except Exception:
        text = await get_text('create_quiz_file_parse_error')
        markup = await reply_kb.back_markup()
        return await message.answer(text, reply_markup=markup)

    question_data = _prepare_question_data(raw_questions)
    if not question_data:
        text = await get_text('create_quiz_file_not_questions')
        return await message.answer(text)

    text = await get_text('create_quiz_part_quantity')
    markup = await reply_kb.quiz_part_quantity_markup()
    await message.answer(text, reply_markup=markup)
    await state.update_data(
        quiz_file_id=message.document.file_id,
        quiz_question_data=question_data,
        quiz_total_questions=len(question_data),
    )
    return await state.set_state(states.CreateQuizState.check)


async def create_quiz_get_quantity_handler(message: types.Message, state: FSMContext):
    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_part_quantity')
        markup = await reply_kb.quiz_part_quantity_markup()
        return await message.answer(text, reply_markup=markup)

    if message.text.startswith('🔙'):
        text = await get_text('create_quiz_file')
        markup = await reply_kb.back_markup()
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.file)

    if not message.text.isdigit() or int(message.text) not in PART_QUESTION_OPTIONS:
        text = await get_text('create_quiz_part_quantity_not_allowed')
        markup = await reply_kb.quiz_part_quantity_markup()
        return await message.answer(text, reply_markup=markup)

    part_size = int(message.text)
    text = await get_text('create_quiz_timer')
    markup = await reply_kb.quiz_timers_markup()
    await message.answer(text, reply_markup=markup)
    await state.update_data(quiz_part_size=part_size)
    return await state.set_state(states.CreateQuizState.timer)


async def create_quiz_get_timer_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()

    if message.content_type != types.ContentType.TEXT:
        text = await get_text('create_quiz_timer')
        return await message.answer(text)

    if message.text.startswith('🔙'):
        text = await get_text('create_quiz_part_quantity')
        markup = await reply_kb.quiz_part_quantity_markup()
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.check)


    texts = await get_texts(('second', 'minute', 'back_text'))
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
        text = await get_text('create_quiz_timer_not_allowed_timer')
        return await message.answer(text)

    timer = _parse_timer_seconds(message.text)

    text = await get_text(
        'create_quiz_check_before_save',
        parameters={
            'title': data.get('quiz_title', ''),
            'timer': message.text,
            'quantity': str(data.get('quiz_total_questions', '')),
            'part_quantity': str(data.get('quiz_part_size', '')),
        }
    )
    markup = await reply_kb.quiz_save_markup()
    await state.update_data(quiz_timer=timer)
    await message.answer(text, reply_markup=markup)
    return await state.set_state(states.CreateQuizState.save)


async def create_quiz_save_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    save_button = await get_text('save_button')

    if message.content_type != types.ContentType.TEXT:
        markup = await reply_kb.quiz_save_markup()
        text = await get_text('use_below_buttons_text')
        return await message.answer(text, reply_markup=markup)

    if message.text and message.text.startswith('🔙'):
        text = await get_text('create_quiz_timer')
        markup = await reply_kb.quiz_timers_markup()
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.timer)

    if message.text != save_button:
        return await message.delete()

    try:
        await create_quiz(message, data, user)
    except Exception:
        text = await get_text('create_quiz_create_error')
        markup = await reply_kb.quiz_save_markup()
        return await message.answer(text, reply_markup=markup)

    text = await get_text('create_quiz_success')
    markup = await reply_kb.remove_kb()
    await state.clear()
    return await message.answer(text, reply_markup=markup)


async def download_file(bot, file_id: str):
    media_dir = Path(settings.BASE_DIR) / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)

    file = await bot.get_file(file_id)
    file_format = Path(file.file_path).suffix.lower().lstrip('.')
    new_file = f"{file.file_id}.{file_format}"
    destination = media_dir / new_file
    await bot.download_file(file.file_path, str(destination))

    return destination, file_format


async def create_quiz(message: types.Message, data: dict, user: TelegramProfile):
    """
    Not handler
    """

    title = data.get('quiz_title', '')
    timer = data.get('quiz_timer', 0)
    file_id = data.get('quiz_file_id', '')
    question_data = data.get('quiz_question_data', [])
    part_size = int(data.get('quiz_part_size', 25))

    total_ques = len(question_data)
    total_parts = total_ques // part_size if not total_ques % part_size else total_ques // part_size + 1

    with transaction.atomic():
        new_quiz = quiz_models.Quiz.objects.create(
            owner_id=user.id,
            title=title[:127],
            file_id=file_id,
            timer=timer,
            quantity=total_ques,
        )

        for i in range(total_parts):
            from_i = i * part_size + 1
            to_i = (i + 1) * part_size if (i + 1) * part_size <= total_ques else total_ques
            quantity = to_i - from_i + 1

            part_title = f"№0{i + 1}" if (i + 1) < 10 else f"№{i + 1}"

            new_part = None
            for _ in range(10):
                link = _generate_unique_link()
                try:
                    new_part = quiz_models.QuizPart.objects.create(
                        quiz_id=new_quiz.id,
                        link=link,
                        from_i=from_i,
                        to_i=to_i,
                        quantity=quantity,
                        title=f"{title[:127]} {part_title}",
                    )
                    break
                except IntegrityError:
                    continue

            if new_part is None:
                raise IntegrityError('Can not generate unique link for quiz part')

            for j in range(quantity):
                row = question_data[i * part_size + j]
                question = quiz_models.Question.objects.create(
                    part_id=new_part.id,
                    text=row['question'],
                )

                options = row['options'][:4]
                correct_norm = _normalize_text(row['correct_answer'])
                correct_index = next(
                    (idx for idx, option in enumerate(options) if _normalize_text(option) == correct_norm),
                    0,
                )
                new_options = []
                for idx, option_text in enumerate(options):
                    new_options.append(
                        quiz_models.Option(
                            question_id=question.id,
                            text=option_text,
                            is_correct=idx == correct_index,
                        )
                    )
                quiz_models.Option.objects.bulk_create(new_options)

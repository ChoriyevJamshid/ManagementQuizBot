import math
import asyncio
from pathlib import Path
from random import choice
from string import ascii_letters, digits

from aiogram import types
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from django.conf import settings
from django.db import transaction
from quiz import models as quiz_models

from bot import utils, states
from bot.keyboards import reply_kb
from bot.utils.functions import get_text, get_texts


ALLOWED_EXTENSIONS = {'docx', 'xlsx', 'txt'}
PART_QUESTION_OPTIONS = {20, 25, 30, 35}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_text(value: str) -> str:
    return ' '.join(str(value).strip().split()).casefold()


def _prepare_question_data(raw_questions: list[dict]) -> list[dict]:
    prepared = []
    for row in raw_questions:
        question = str(row.get('question', '')).strip()[:512]
        correct_answer = str(row.get('correct_answer', '')).strip()[:512]
        options_raw = row.get('options') or []

        cleaned_options = [
            str(o).strip()[:512]
            for o in options_raw
            if str(o).strip()
        ]

        if not question or len(cleaned_options) < 4:
            continue

        correct_norm = _normalize_text(correct_answer)
        correct_in_options = next(
            (o for o in cleaned_options if _normalize_text(o) == correct_norm),
            None,
        )
        if correct_in_options is None:
            continue

        options = cleaned_options[:4]
        if correct_in_options not in options:
            options = cleaned_options[:3] + [correct_in_options]

        prepared.append({
            'question': question,
            'correct_answer': correct_in_options,
            'options': options,
        })

    return prepared


def _parse_timer_seconds(timer_text: str) -> int:
    """Values < 10 are treated as minutes, >= 10 as seconds."""
    total = 0
    for token in timer_text.split():
        if token.isdigit():
            v = int(token)
            total += v * 60 if v < 10 else v
    return total


def _unique_link(length: int = 8) -> str:
    """Generates a unique QuizPart link. Runs inside a sync thread."""
    symbols = ascii_letters + digits
    while True:
        link = ''.join(choice(symbols) for _ in range(length))
        if not quiz_models.QuizPart.objects.filter(link=link).exists():
            return link


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def create_quiz_handler(callback: types.CallbackQuery, state: FSMContext):
    """Entry point — show step-by-step intro, then ask for title."""
    text = await get_text('create_quiz_intro')
    await callback.message.edit_text(text)
    await callback.answer()
    await state.set_state(states.CreateQuizState.title)


async def create_quiz_get_title_handler(message: types.Message, state: FSMContext):
    if message.content_type != types.ContentType.TEXT:
        return await message.answer(await get_text('create_quiz_intro'))

    if message.text.startswith('/'):
        await message.answer(await get_text('create_quiz_not_allowed_title'))
        return await message.delete()

    await state.update_data(quiz_title=message.text.strip())
    markup = await reply_kb.back_markup()
    await message.answer(await get_text('create_quiz_file'), reply_markup=markup)
    await state.set_state(states.CreateQuizState.file)


async def create_quiz_get_file_handler(message: types.Message, state: FSMContext):
    if message.text:
        if message.text.startswith('🔙'):
            markup = await reply_kb.remove_kb()
            await message.answer(await get_text('create_quiz_intro'), reply_markup=markup)
            return await state.set_state(states.CreateQuizState.title)
        return await message.delete()

    if not message.document:
        markup = await reply_kb.back_markup()
        return await message.answer(await get_text('create_quiz_file_not_document'), reply_markup=markup)

    extension = Path(message.document.file_name or '').suffix.lower().lstrip('.')
    if extension not in ALLOWED_EXTENSIONS:
        markup = await reply_kb.back_markup()
        return await message.answer(await get_text('create_quiz_file_not_correct_extension'), reply_markup=markup)

    processing_msg = await message.answer(await get_text('create_quiz_processing_file'))

    try:
        file_path, file_format = await _download_file(message.bot, message.document.file_id)

        if file_format == 'docx':
            raw_questions = await asyncio.to_thread(_parse_docx_sync, str(file_path))
        elif file_format == 'xlsx':
            raw_questions = await asyncio.to_thread(_parse_xlsx_sync, str(file_path))
        else:
            raw_questions = await asyncio.to_thread(_parse_txt_sync, str(file_path))
    except Exception:
        await processing_msg.delete()
        markup = await reply_kb.back_markup()
        return await message.answer(await get_text('create_quiz_file_parse_error'), reply_markup=markup)

    question_data = _prepare_question_data(raw_questions)
    await processing_msg.delete()

    if not question_data:
        return await message.answer(await get_text('create_quiz_file_not_questions'))

    await state.update_data(
        quiz_file_id=message.document.file_id,
        quiz_question_data=question_data,
        quiz_total_questions=len(question_data),
    )

    text = await get_text('create_quiz_part_quantity', {'total': str(len(question_data))})
    markup = await reply_kb.quiz_part_quantity_markup()
    await message.answer(text, reply_markup=markup)
    await state.set_state(states.CreateQuizState.check)


async def create_quiz_get_quantity_handler(message: types.Message, state: FSMContext):
    if message.content_type != types.ContentType.TEXT:
        markup = await reply_kb.quiz_part_quantity_markup()
        return await message.answer(await get_text('create_quiz_part_quantity_not_allowed'), reply_markup=markup)

    if message.text.startswith('🔙'):
        markup = await reply_kb.back_markup()
        await message.answer(await get_text('create_quiz_file'), reply_markup=markup)
        return await state.set_state(states.CreateQuizState.file)

    if not message.text.isdigit() or int(message.text) not in PART_QUESTION_OPTIONS:
        markup = await reply_kb.quiz_part_quantity_markup()
        return await message.answer(await get_text('create_quiz_part_quantity_not_allowed'), reply_markup=markup)

    part_size = int(message.text)
    await state.update_data(quiz_part_size=part_size)
    markup = await reply_kb.quiz_timers_markup()
    await message.answer(await get_text('create_quiz_timer'), reply_markup=markup)
    await state.set_state(states.CreateQuizState.timer)


async def create_quiz_get_timer_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()

    if message.content_type != types.ContentType.TEXT:
        return await message.answer(await get_text('create_quiz_timer'))

    if message.text.startswith('🔙'):
        markup = await reply_kb.quiz_part_quantity_markup()
        text = await get_text('create_quiz_part_quantity', {
            'total': str(data.get('quiz_total_questions', 0))
        })
        await message.answer(text, reply_markup=markup)
        return await state.set_state(states.CreateQuizState.check)

    texts = await get_texts(('second', 'minute'))
    valid_timers = (
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

    if message.text not in valid_timers:
        return await message.answer(await get_text('create_quiz_timer_not_allowed_timer'))

    timer = _parse_timer_seconds(message.text)
    total_questions = data.get('quiz_total_questions', 0)
    part_size = data.get('quiz_part_size', 25)
    parts_count = math.ceil(total_questions / part_size)

    await state.update_data(quiz_timer=timer, quiz_parts_count=parts_count)

    text = await get_text('create_quiz_check_before_save', {
        'title':         data.get('quiz_title', ''),
        'quantity':      str(total_questions),
        'part_quantity': str(part_size),
        'parts':         str(parts_count),
        'timer':         message.text,
    })
    markup = await reply_kb.quiz_save_markup()
    await message.answer(text, reply_markup=markup)
    await state.set_state(states.CreateQuizState.save)


async def create_quiz_save_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.from_user)
    save_button = await get_text('save_button')

    if message.content_type != types.ContentType.TEXT:
        markup = await reply_kb.quiz_save_markup()
        return await message.answer(await get_text('use_below_buttons_text'), reply_markup=markup)

    if message.text.startswith('🔙'):
        markup = await reply_kb.quiz_timers_markup()
        await message.answer(await get_text('create_quiz_timer'), reply_markup=markup)
        return await state.set_state(states.CreateQuizState.timer)

    if message.text != save_button:
        return await message.delete()

    saving_msg = await message.answer(await get_text('create_quiz_saving'))

    try:
        await sync_to_async(_create_quiz_sync)(data, user.id)
    except Exception:
        await saving_msg.delete()
        markup = await reply_kb.quiz_save_markup()
        return await message.answer(await get_text('create_quiz_create_error'), reply_markup=markup)

    await saving_msg.delete()
    markup = await reply_kb.remove_kb()
    await state.clear()
    await message.answer(await get_text('create_quiz_success'), reply_markup=markup)


# ---------------------------------------------------------------------------
# File download
# ---------------------------------------------------------------------------

async def _download_file(bot, file_id: str) -> tuple[Path, str]:
    media_dir = Path(settings.BASE_DIR) / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    file = await bot.get_file(file_id)
    file_format = Path(file.file_path).suffix.lower().lstrip('.')
    destination = media_dir / f"{file.file_id}.{file_format}"
    await bot.download_file(file.file_path, str(destination))
    return destination, file_format


# ---------------------------------------------------------------------------
# Sync file parsers — called via asyncio.to_thread
# ---------------------------------------------------------------------------

def _parse_docx_sync(file_path: str) -> list[dict]:
    import docx
    data = []
    for table in docx.Document(file_path).tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) < 3 or len(cells) > 6:
                continue
            question = str(cells[0].text).strip()[:256]
            correct_answer = str(cells[1].text).strip()[:512]
            options = [str(cells[i].text).strip()[:512] for i in range(1, len(cells)) if cells[i].text.strip()]
            if question and len(options) >= 2:
                data.append({'question': question, 'correct_answer': correct_answer, 'options': options})
    return data


def _parse_xlsx_sync(file_path: str) -> list[dict]:
    import pandas as pd
    data = []
    raw = pd.read_excel(file_path, engine='openpyxl', header=None)
    df = pd.DataFrame(raw).fillna('')
    for _, raw_row in df.iterrows():
        cells = [str(v).strip()[:512] for v in raw_row]
        if len(cells) < 2:
            continue
        question = cells[0]
        correct_answer = cells[1]
        options = [c for c in cells[1:] if c]
        if question and len(options) >= 2:
            data.append({'question': question, 'correct_answer': correct_answer, 'options': options})
    return data


def _parse_txt_sync(file_path: str) -> list[dict]:
    data = []
    current: dict = {'options': []}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            if 'question' not in current:
                current['question'] = text
            elif 'correct_answer' not in current:
                current['correct_answer'] = text
                current['options'].append(text)
            else:
                current['options'].append(text)
                if len(current['options']) == 4:
                    data.append(current)
                    current = {'options': []}
    return data


# ---------------------------------------------------------------------------
# DB write — sync, called via sync_to_async
# ---------------------------------------------------------------------------

def _create_quiz_sync(data: dict, owner_id: int) -> None:
    title     = data.get('quiz_title', '')
    timer     = data.get('quiz_timer', 0)
    file_id   = data.get('quiz_file_id', '')
    questions = data.get('quiz_question_data', [])
    part_size = int(data.get('quiz_part_size', 25))
    total     = len(questions)

    with transaction.atomic():
        quiz = quiz_models.Quiz.objects.create(
            owner_id=owner_id,
            title=title[:127],
            file_id=file_id,
            timer=timer,
            quantity=total,
        )

        for part_idx in range(math.ceil(total / part_size)):
            from_i   = part_idx * part_size + 1
            to_i     = min((part_idx + 1) * part_size, total)
            quantity = to_i - from_i + 1
            part_num = f"№0{part_idx + 1}" if part_idx + 1 < 10 else f"№{part_idx + 1}"

            part = quiz_models.QuizPart.objects.create(
                quiz_id=quiz.id,
                link=_unique_link(),
                from_i=from_i,
                to_i=to_i,
                quantity=quantity,
                title=f"{title[:127]} {part_num}",
            )

            part_questions = questions[part_idx * part_size: part_idx * part_size + quantity]

            # 1 query for all questions in this part
            created_questions = quiz_models.Question.objects.bulk_create([
                quiz_models.Question(part_id=part.id, text=row['question'])
                for row in part_questions
            ])

            # 1 query for all options in this part
            options_batch = []
            for question_obj, row in zip(created_questions, part_questions):
                correct_norm = _normalize_text(row['correct_answer'])
                for option_text in row['options'][:4]:
                    options_batch.append(
                        quiz_models.Option(
                            question_id=question_obj.id,
                            text=option_text,
                            is_correct=_normalize_text(option_text) == correct_norm,
                        )
                    )
            quiz_models.Option.objects.bulk_create(options_batch)

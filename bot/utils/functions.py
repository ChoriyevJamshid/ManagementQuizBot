import asyncio
import logging
import orjson
import docx
import pandas as pd
from random import choice, shuffle
from string import ascii_letters, digits
from typing import Optional, Dict
from django.conf import settings
from aiogram import types

logger = logging.getLogger(__name__)

# Module-level text cache — populated once on first call, never reloaded.
_text_cache: dict | None = None


def _get_lang_file_path() -> str:
    return f"{settings.BASE_DIR}/languages/uz.json"


def _load_cache() -> dict:
    """Load uz.json into memory once. Subsequent calls return the cached dict."""
    global _text_cache
    if _text_cache is None:
        with open(_get_lang_file_path(), mode='rb') as f:
            _text_cache = orjson.loads(f.read())
    return _text_cache


def _apply_params(text: str, parameters: Optional[Dict[str, str]]) -> str:
    if parameters:
        for key, value in parameters.items():
            text = text.replace(f"__{key}", value)
    return text.strip()


# ─── Sync API ────────────────────────────────────────────────────────────────

def get_text_sync(code: str, parameters: Optional[Dict[str, str]] = None) -> str:
    data = _load_cache()
    text = data.get(code)
    if text is None:
        logger.warning("Missing text key: %r", code)
        return ''
    return _apply_params(text, parameters)


def get_texts_sync(codes: tuple | list) -> dict:
    data = _load_cache()
    result = {}
    for code in codes:
        text = data.get(code)
        if text is None:
            logger.warning("Missing text key: %r", code)
            result[code] = ''
        else:
            result[code] = text.strip()
    return result


# ─── Async API (thin wrappers — no I/O, no coroutine overhead after startup) ─

async def get_text(code: str, parameters: Optional[Dict[str, str]] = None) -> str:
    return get_text_sync(code, parameters)


async def get_texts(codes: tuple | list) -> dict:
    return get_texts_sync(codes)


# ─── File parsers ─────────────────────────────────────────────────────────────

async def get_data_from_document(file_path, only_count=False):
    data = []
    document = docx.Document(file_path)
    count = 0
    for table in document.tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) < 3 or len(cells) > 6:
                continue

            question = str(row.cells[0].text).strip()[:256]
            correct_answer = row.cells[1].text
            options = []

            for i in range(1, len(cells)):
                option = str(cells[i].text).strip()[:512]
                if option:
                    options.append(option)

            if question and len(options) >= 2:
                if not only_count:
                    data.append({
                        'question': question,
                        'correct_answer': correct_answer,
                        'options': options,
                    })
                else:
                    count += 1
    if only_count:
        return count
    return data


async def get_data_from_xlsx(file_path: str, only_count=False):
    _data = []
    count = 0
    df = pd.read_excel(file_path, engine="openpyxl", header=None)

    for _, row in df.iterrows():
        row = row.fillna("")

        question = str(row.iloc[0]).strip()[:512]
        correct_answer = str(row.iloc[1]).strip()[:512]
        options = []
        for i in range(1, len(row)):
            option = str(row.iloc[i]).strip()[:512]
            if option:
                options.append(option)

        if question and len(options) >= 2:
            if not only_count:
                _data.append({
                    'question': question,
                    'correct_answer': correct_answer,
                    'options': options,
                })
            else:
                count += 1
    if only_count:
        return count
    return _data


async def get_data_from_txt(file_path: str, only_count=False):
    data = []
    count = 0
    current_question = {"options": []}
    with open(file_path, "r", encoding="utf-8") as f:
        for row in f.readlines():
            text = row.strip()

            if text == '':
                continue

            question = current_question.get('question', None)
            if question is None:
                current_question['question'] = text
                continue

            correct_answer = current_question.get('correct_answer', None)
            if correct_answer is None:
                current_question['correct_answer'] = text

            current_question['options'].append(text)

            if len(current_question.get('options', [])) == 4:
                if only_count is False:
                    data.append(current_question)
                else:
                    count += 1
                current_question = {"options": []}

    if only_count:
        return count
    return data


async def generate_unique_link(length: int = 8):
    result = ""
    symbols = tuple(ascii_letters + digits)
    for i in range(length):
        result += choice(symbols)
    return result


async def testing_animation(callback: types.CallbackQuery):
    """Individual quiz start animation. Uses asyncio.sleep — does NOT block event loop."""
    animation_number = 2
    nums = ('1️⃣', '2️⃣', '3️⃣')
    texts = get_texts_sync(('are_you_ready', 'starting', 'go_go'))
    texts_list = list(texts.values())

    await callback.message.delete_reply_markup()
    msg = await callback.message.answer(f"{nums[animation_number]}...")
    for i in range(1, 3):
        await asyncio.sleep(1)
        try:
            msg = await callback.bot.edit_message_text(
                text=f"{nums[animation_number - i]}{texts_list[i - 1]}...",
                chat_id=callback.message.chat.id,
                message_id=msg.message_id,
            )
        except Exception:
            pass
    await asyncio.sleep(1)
    try:
        await callback.bot.edit_message_text(
            text=texts_list[-1],
            chat_id=callback.message.chat.id,
            message_id=msg.message_id,
        )
    except Exception:
        pass
    await asyncio.sleep(1)
    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=msg.message_id,
        )
    except Exception:
        pass


async def generate_user_quiz_data(part):
    data = []
    for question in part.questions.all():
        qs = {
            'question': question.text,
            "options": [],
            'correct_option': None
        }
        for option in question.options.all():
            qs['options'].append(option.text)
            if option.is_correct:
                qs['correct_option'] = option.text
        shuffle(qs['options'])
        data.append(qs)
    shuffle(data)
    return data


def reform_spent_time(spent_time: float | int) -> str:
    minutes = int(spent_time // 60)
    seconds = round(spent_time % 60, 2)
    if minutes > 0:
        return f"{minutes} min {seconds} sec"
    return f"{seconds} sec"


def create_excel_statistics(
        file_path: str,
        sorted_players: list | tuple,
        quantity: int,
        timer: int = 0,
):
    cols_name = {
        'name': "FIO",
        'corrects': "To'g'ri javoblar",
        'wrongs': "Noto'g'ri javoblar",
        'spent_time': "Sarf qilingan vaqt",
        'percent': "Foiz",
    }
    excel_data = []
    for _, player_data in sorted_players:
        corrects = player_data.get('corrects', 0)
        wrongs = player_data.get('wrongs', 0)
        raw_time = player_data.get('spent_time', 0)

        if corrects == 0 and wrongs == 0:
            continue

        skips = max(0, quantity - corrects - wrongs)
        total_time = raw_time + (timer * skips)

        percent = round(corrects / quantity * 100, 2) if quantity else 0
        formatted_time = reform_spent_time(total_time)

        excel_data.append({
            cols_name["name"]: player_data.get('username'),
            cols_name["corrects"]: corrects,
            cols_name["wrongs"]: wrongs,
            cols_name["spent_time"]: formatted_time,
            cols_name["percent"]: f"{percent}%",
        })

    df = pd.DataFrame(excel_data, columns=list(cols_name.values()))
    df.to_excel(file_path, index=False)




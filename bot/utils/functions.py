import time
import orjson
import aiofiles
import docx
import pandas as pd
from random import choice, shuffle
from string import ascii_letters, digits
from typing import Optional, Dict
from django.conf import settings
from aiogram import types


def get_text_sync(code: str, language: str, parameters: Optional[Dict[str, str]] = None) -> str:
    file_path = f"{settings.BASE_DIR}/languages/{language}.json"

    with open(file_path, mode='rb') as file:
        content = file.read()

    data = orjson.loads(content)
    text = data.get(code, '')

    print(f"\n{parameters = }\n")
    print(f"{text = }\n")
    if parameters and text is not None:
        for key, value in parameters.items():
            text = text.replace(f"__{key}", value)

    return text.strip()


def get_texts_sync(codes: tuple | list, language: str) -> dict:
    file_path = f"{settings.BASE_DIR}/languages/{language}.json"

    with open(file_path, mode='rb') as file:
        content = file.read()

    data = orjson.loads(content)
    return {code: data.get(code, '').strip() for code in codes}


async def get_text(code: str, language: str, parameters: Optional[Dict[str, str]] = None) -> str:
    file_path = f"{settings.BASE_DIR}/languages/{language}.json"

    async with aiofiles.open(file_path, mode='rb') as file:
        content = await file.read()

    data = orjson.loads(content)
    text = data.get(code, '')

    if parameters and text is not None:
        for key, value in parameters.items():
            text = text.replace(f"__{key}", value)

    return text.strip()


async def get_texts(codes: tuple | list, language: str) -> dict:
    file_path = f"{settings.BASE_DIR}/languages/{language}.json"

    async with aiofiles.open(file_path, mode='rb') as file:
        content = await file.read()

    data = orjson.loads(content)
    return {code: data.get(code, '').strip() for code in codes}


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
        for index, row in enumerate(f.readlines(), start=1):
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


async def testing_animation(callback: types.CallbackQuery, language):
    animation_number = 2
    nums = ('1️⃣', '2️⃣', '3️⃣')
    texts = await get_texts(('are_you_ready', 'starting', 'go_go'), language)
    texts = list(texts.values())

    await callback.message.delete_reply_markup()
    msg = await callback.message.answer(f"{nums[animation_number]}...")
    for i in range(1, 3):
        time.sleep(1)
        msg = await callback.bot.edit_message_text(
            text=f"{nums[animation_number - i]}{texts[i - 1]}...",
            chat_id=callback.message.chat.id,
            message_id=msg.message_id,
        )
    time.sleep(1)
    await callback.bot.edit_message_text(
        text=f"{texts[-1]}",
        chat_id=callback.message.chat.id,
        message_id=msg.message_id
    )
    time.sleep(1)
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=msg.message_id
    )


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


def reform_spent_time(spent_time: float | int):
    """
    spent_time: float | int - this argument get time on types: int, float
    """

    formatted_text = str()
    minutes = spent_time // 60
    seconds = round(spent_time % 60, 2)

    if minutes > 0:
        formatted_text += f"{minutes} min "
    formatted_text += f"{seconds} sec"
    return formatted_text


def create_excel_statistics(
        file_path: str,
        sorted_players: list | tuple,
        quantity: int,
        language: str = "en",
):
    cols_name = {
        'name': {
            'en': "Full Name",
            'uz': "FIO",
            'ru': "ФИО"
        },
        'corrects': {
            'en': "Corrects",
            'uz': "To‘g‘ri javoblar",
            'ru': "Правильные ответы"
        },
        'wrongs': {
            'en': "Wrongs",
            'uz': "Noto‘g‘ri javoblar",
            'ru': "Неправильные ответы"
        },
        'spent_time': {
            'en': "Spend Time",
            'uz': "Sarf qilingan vaqt",
            'ru': "Затраченное время"
        },
        'percent': {
            'en': "Percent",
            'uz': "Foiz",
            'ru': "Процент"
        }

    }
    excel_data = []
    print(f"\n{sorted_players = }\n")
    for _, player_data in sorted_players:

        if player_data.get('spent_time', 0) == 0:
            continue

        percent = round(player_data.get('corrects', 0) / quantity * 100, 2)
        formatted_time = reform_spent_time(player_data.get('spent_time'))

        excel_data.append({
            cols_name["name"][language]: player_data.get('username'),
            cols_name["corrects"][language]: player_data.get('corrects'),
            cols_name["wrongs"][language]: player_data.get('wrongs'),
            cols_name["spent_time"][language]: formatted_time,
            cols_name["percent"][language]: f"{percent}%",
        })

    columns = []
    for col_name in cols_name.values():
        columns.append(col_name[language])

    df = pd.DataFrame(
        excel_data,
        columns=columns,
    )
    df.to_excel(file_path, index=False)



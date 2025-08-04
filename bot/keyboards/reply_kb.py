from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from bot import utils
from bot.utils.functions import get_text, get_texts


async def back_markup(language: str):
    text = await get_text('back_text', language)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def quiz_category_markup(language: str, state: FSMContext):
    iterator = 1
    categories = await utils.get_categories()
    texts = await get_texts([category['title'] for category in categories], language)

    builder = ReplyKeyboardBuilder()
    for code, value in texts.items():
        builder.add(
            KeyboardButton(text=f"#{iterator}. {value}"),
        )
        iterator += 1

    _builder = ReplyKeyboardBuilder().add(KeyboardButton(text=await get_text('back_text', language)))
    return builder.adjust(*(2,)).attach(_builder).as_markup(
        resize_keyboard=True
    )


async def quiz_timers_markup(language: str, without_back: bool = False):
    texts = await get_texts(('second', 'minute', 'back_text'), language)
    timers = [
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
    ]
    if not without_back:
        timers.append(texts['back_text'])

    builder = ReplyKeyboardBuilder()
    for timer in timers:
        builder.add(KeyboardButton(text=timer))
    return builder.adjust(*(3, 3, 2, 2, 1,)).as_markup(resize_keyboard=True)


async def quiz_save_markup(language: str):
    texts = await get_texts(('save_button', 'back_text'), language)
    buttons = (
        f"{texts['save_button']}",
        f"{texts['back_text']}",
    )

    builder = ReplyKeyboardBuilder()
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    return builder.adjust(*(1,)).as_markup(resize_keyboard=True)


async def back_to_pending_messaged_markup():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def share_contact_markup(text: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text, request_contact=True)]
        ],
        resize_keyboard=True,
    )

async def remove_kb():
    return ReplyKeyboardRemove()

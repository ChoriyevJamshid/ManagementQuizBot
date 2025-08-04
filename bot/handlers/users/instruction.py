from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb
from bot.states import MainState
from bot.utils.functions import get_text


async def instruction_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    text = await get_text("instruction_choice_file_type", language)
    markup = await inline_kb.instruction_choice_file_type_markup(language)

    await callback.message.edit_text(text, reply_markup=markup)
    await state.set_state(MainState.instruction)
    await callback.answer()


async def instruction_file_type_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    data_solo = await utils.get_data_solo()
    file_type = callback.data.split('_')[-1]
    video_url = data_solo.video_urls.get(file_type, {}).get('url', '')

    text = await get_text(f"instruction_{file_type}", language, {
        'url': video_url,
    })
    markup = await inline_kb.instruction_back_markup()

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def instruction_back_to_instruction(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    text = await get_text("instruction_choice_file_type", language)
    markup = await inline_kb.instruction_choice_file_type_markup(language)

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()

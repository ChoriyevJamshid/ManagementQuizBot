from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot import states
from bot.keyboards import inline_kb, reply_kb
from bot.utils.functions import get_text, get_texts
from bot.handlers.users.quizzes import quiz_list_handler
from bot.handlers.users.create_quizzes import create_quiz_handler
from bot.handlers.users.instruction import instruction_handler


async def start_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)

    if not user.is_registered:
        texts = await get_texts(
            ('user_share_contact_for_register_text', 'share_contact_text')
        )
        await message.answer(
            text=texts['user_share_contact_for_register_text'],
            reply_markup=await reply_kb.share_contact_markup(text=texts['share_contact_text'])
        )
        await state.set_state(states.MainState.share_contact)
        return

    markup = await inline_kb.main_menu_markup()
    text = await get_text('main_menu')

    await state.update_data(markup_message_id=message.message_id + 1)
    await state.set_state(states.MainState.main_menu)
    await message.answer(text, reply_markup=markup)


async def help_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    text = await get_text('help')
    await message.answer(text)


async def cancel_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)

    current_state = await state.get_state()
    if current_state and current_state.startswith("CreateQuizState"):
        markup = await inline_kb.main_menu_markup()
        text = await get_texts(('main_menu', 'cancel_text'))
        await message.answer(text['cancel_text'], reply_markup=await reply_kb.remove_kb())
        await message.answer(text['main_menu'], reply_markup=markup)
        await state.update_data(markup_message_id=message.message_id + 1)
        return await state.set_state(states.MainState.main_menu)
    return await message.delete()


async def main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'menu-quizzes':
        await quiz_list_handler(callback, state)
    elif callback.data == "menu-create-quiz":
        await create_quiz_handler(callback, state)
    elif callback.data == "menu-instruction":
        await instruction_handler(callback, state)
    else:
        await callback.answer()


async def get_user_contact_handler(message: types.Message, state: FSMContext):

    user = await utils.get_user(message.from_user)
    if message.content_type != types.ContentType.CONTACT:

        text = await get_text('please_send_contact_for_register')
        return await message.reply(text)

    user.phone_number = str(message.contact.phone_number)
    user.is_registered = True
    markup = await inline_kb.main_menu_markup()
    texts = await get_texts(('main_menu', 'registered_success_text'))

    await message.answer(texts['registered_success_text'], reply_markup=await reply_kb.remove_kb())
    await message.answer(texts['main_menu'], reply_markup=markup)

    await state.set_state(states.MainState.main_menu)
    await state.update_data(markup_message_id=message.message_id + 2)
    return await user.asave(update_fields=['phone_number', 'is_registered', 'updated_at'])


async def delete_message_handler(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except Exception as e:
        pass


async def delete_callback_handler(callback: types.CallbackQuery, state: FSMContext):

    user = await utils.get_user(callback.from_user)
    text = await get_text('please_press_start')
    try:
        await callback.message.delete()
    except Exception as e:
        pass

    await callback.bot.send_message(
        chat_id=user.chat_id,
        text=text
    )



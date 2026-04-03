from utils.choices import Role

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb
from bot.states import MainState
from bot.utils.functions import get_text, get_texts


async def admin_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.chat)

    if user.role == Role.USER:
        return await message.delete()

    if data.get('markup_message_id', None) is not None:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=data.get('markup_message_id', 1),
                reply_markup=None,
            )
        except Exception:
            pass

    texts = await get_texts((
        'admin_menu',
        'admin_user_count_button',
    ))

    markup = await inline_kb.admin_menu_markup(texts)

    await state.update_data(markup_message_id=message.message_id + 1)
    await message.answer(texts['admin_menu'], reply_markup=markup)
    return await state.set_state(MainState.admin)


async def admin_user_count_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    users_number = await utils.get_users_count()
    text = await get_text('admin_users_count_text', {'count': str(users_number)})

    return await callback.answer(text, show_alert=True)


async def admin_back_admin_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    texts = await get_texts((
        'admin_menu',
        'admin_user_count_button',
    ))

    markup = await inline_kb.admin_menu_markup(texts)
    await state.update_data(markup_message_id=callback.message.message_id)
    await callback.message.edit_text(texts['admin_menu'], reply_markup=markup)
    return await callback.answer()

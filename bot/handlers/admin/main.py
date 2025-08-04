import os, json
from django.conf import settings

from utils.choices import Role

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.keyboards import inline_kb, reply_kb
from bot.states import MainState
from bot.utils.functions import get_text, get_texts


async def admin_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.chat)
    language = user.language if user.language else 'en'
    message_id = data.get('markup_message_id', None)

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
        'admin_support_messages_count_button',
        'admin_support_pending_messages_button',
    ), language)

    markup = await inline_kb.admin_menu_markup(texts)

    if message_id is not None:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=message_id,
                reply_markup=None,
            )
        except Exception as e:
            pass

    await state.update_data(markup_message_id=message.message_id + 1)
    await message.answer(texts['admin_menu'], reply_markup=markup)
    return await state.set_state(MainState.admin)


async def admin_user_count_callback(callback: types.CallbackQuery, state: FSMContext):

    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    users_number = await utils.get_users_count()
    text = await get_text('admin_users_count_text', language, {'count': str(users_number)})

    return await callback.answer(text, show_alert=True)


async def admin_support_messages_count_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    messages_counts = await utils.get_support_messages_count()
    text = await get_text('admin_support_messages_count_text', language, {
        'all': str(messages_counts.get('all', 0)),
        'pending': str(messages_counts.get('pending', 0)),
        'resolved': str(messages_counts.get('resolved', 0)),
        'rejected': str(messages_counts.get('rejected', 0)),
    })

    return await callback.answer(text, show_alert=True)


async def admin_support_pending_messages_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    pending_messages = await utils.get_pending_messages()

    if not pending_messages:
        text = await get_text('admin_support_not_pending_messages_text', language)
        return await callback.answer(text, show_alert=True)

    text = str()
    ids = []
    for number, pending_message in enumerate(pending_messages, start=1):
        text += f"#<b>{number}</b>. ID: <code>{pending_message.id}</code>\n" \
                f"Question: {pending_message.question}\n\n"
        ids.append(pending_message.id)

    markup = await inline_kb.admin_pending_message_markup(ids)
    await callback.message.edit_text(text, reply_markup=markup)
    return await callback.answer()


async def admin_pending_message_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        user = await utils.get_user(callback.from_user)
        language = user.language if user.language else 'en'

        if user.role == Role.USER:
            await callback.answer()
            return await callback.message.delete()

        pending_id = callback.data.split('_')[-1]
        text = await get_text('admin_answer_to_pending_message_text', language)
        markup = await reply_kb.back_to_pending_messaged_markup()


        await callback.message.delete_reply_markup()
        await callback.message.reply(text, reply_markup=markup)
        await state.update_data(pending_id=pending_id)
        await state.set_state(MainState.admin_write)
        return await callback.answer()
    except Exception as e:
        print(f"\n{e = }\n")

    finally:
        await callback.answer()


async def get_admin_answer_to_pending_message_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = await utils.get_user(message.chat)
    language = user.language if user.language else 'en'

    if message.content_type != types.ContentType.TEXT:
        text = await get_text('admin_answer_to_pending_message_text', language)
        markup = await reply_kb.back_to_pending_messaged_markup()
        return await message.answer(text, reply_markup=markup)

    if message.text == "🔙":

        pending_messages = await utils.get_pending_messages()

        if not pending_messages:
            text = await get_text('admin_support_not_pending_messages_text', language)
            texts = await get_texts((
                'admin_menu',
                'admin_user_count_button',
                'admin_support_messages_count_button',
                'admin_support_pending_messages_button',
            ), language)

            markup = await inline_kb.admin_menu_markup(texts)
            await state.update_data(markup_message_id=message.message_id + 1)
            return await message.answer(text, reply_markup=markup)

    pending_id = int(data.get('pending_id', 0))
    pending_message = await utils.get_support_message(message_id=pending_id)

    texts = await get_texts((
        'admin_menu',
        'admin_user_count_button',
        'admin_support_messages_count_button',
        'admin_support_pending_messages_button',
    ), language)
    markup = await inline_kb.admin_menu_markup(texts)

    if not pending_message:
        text = await get_text('admin_support_not_pending_messages_text', language)
        return await message.answer(text, reply_markup=markup)

    pending_message.answer = message.text
    pending_message.status = 'resolved'

    text = await get_text('admin_answer_to_pending_message_success_text', language)
    await message.answer(text, reply_markup=markup)
    await state.clear()
    await state.update_data(markup_message_id=message.message_id + 1)
    return await pending_message.asave()


async def admin_back_admin_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    if user.role == Role.USER:
        await callback.answer()
        return await callback.message.delete()

    texts = await get_texts((
        'admin_menu',
        'admin_user_count_button',
        'admin_support_messages_count_button',
        'admin_support_pending_messages_button',
    ), language)

    markup = await inline_kb.admin_menu_markup(texts)
    await state.update_data(markup_message_id=callback.message.message_id)
    await callback.message.edit_text(texts['admin_menu'], reply_markup=markup)
    return await callback.answer()







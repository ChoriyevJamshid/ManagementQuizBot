from aiogram import types
from aiogram.fsm.context import FSMContext

from support.choices import SupportMessageStatus

from bot import utils
from bot.keyboards import inline_kb
from bot.states import SupportState
from bot.utils.functions import get_text, get_texts


async def support_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    texts = await get_texts((
        "support_menu_text", 'appeal_to_admin_button',
        'add_category_button', 'testing_questions_file'
    ), language)
    markup = await inline_kb.support_menu_markup(texts)

    await callback.message.edit_text(text=texts['support_menu_text'], reply_markup=markup)
    await state.update_data(markup_message_id=callback.message.message_id)
    await callback.answer()
    await state.set_state(SupportState.support)


async def support_appeal_to_admin_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    texts = await get_texts((
        'support_appeal_to_admin_menu_text',
        'writen_messages_button',
        'write_new_message_button'
    ), language)
    markup = await inline_kb.support_appeal_to_admin_markup(texts)

    await callback.message.edit_text(
        text=texts['support_appeal_to_admin_menu_text'],
        reply_markup=markup
    )


async def support_appeal_to_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    _ = callback.data.split('_')[-1]
    if _ == 'messages':
        return await support_messages(callback, state)

    elif _ == "newMessage":
        return await support_write_new_message(callback, state)
    else:
        return await callback.answer()


async def support_messages(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    messages = await utils.get_support_messages(user.id)
    if not messages:
        text = await get_text("support_messages_not_found", language)
        return await callback.answer(text, show_alert=True)

    texts = await get_texts((
        'message_text',
        'question_text',
        'answer_text',
        'not_answered_text',
        'status_text',
        'is_read_text',
        'already_read_text',
        'not_read_yet_text',
        'me_read_text',
    ), language)
    await callback.answer()
    for _message in messages:
        _answer = texts['not_answered_text'] if not _message.answer else _message.answer
        _read = texts['already_read_text'] if _message.is_read else texts['not_read_yet_text']
        _status = "✅"
        if _message.status == SupportMessageStatus.PENDING:
            _status = "⏳"
        if _message.status == SupportMessageStatus.REJECTED:
            _status = "❌"
        text = (f"\n🆔 {texts['message_text']}: <i>{_message.id}</i>"
                f"\n📜 {texts['question_text']}:"
                f"\n<i>{_message.question}</i>"
                f"\n\n💬 {texts['answer_text']}:"
                f"\n<i>{_answer}</i>"
                f"\n\n📌 {texts['status_text']}: {_status}"
                f"\n📖 {texts['is_read_text']}: 📩 {_read}")

        markup = await inline_kb.support_message_markup(_message.id, texts)
        if _message.status == SupportMessageStatus.PENDING:
            markup = None
        await callback.message.answer(text=text, reply_markup=markup)


async def support_mark_message_as_read_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    message_id = int(callback.data.split('_')[-1])
    _message = await utils.get_support_message(message_id)

    if not _message:
        return await callback.answer()

    _message.is_read = True
    if _message.status == SupportMessageStatus.PENDING:
        _message.status = SupportMessageStatus.REJECTED
    _message.save(update_fields=['is_read', 'status'])

    texts = await get_texts((
        'message_text',
        'question_text',
        'answer_text',
        'not_answered_text',
        'status_text',
        'is_read_text',
        'already_read_text',
        'not_read_yet_text',
        'me_read_text',
    ), language)

    _answer = texts['not_answered_text'] if not _message.answer else _message.answer
    _read = texts['already_read_text'] if _message.is_read else texts['not_read_yet_text']
    _status = "✅"
    if _message.status == SupportMessageStatus.PENDING:
        _status = "⏳"
    if _message.status == SupportMessageStatus.REJECTED:
        _status = "❌"
    text = (f"\n🆔 {texts['message_text']}: <i>{_message.id}</i>"
            f"\n📜 {texts['question_text']}:"
            f"\n<i>{_message.question}</i>"
            f"\n\n💬 {texts['answer_text']}:"
            f"\n<i>{_answer}</i>"
            f"\n\n📌 {texts['status_text']}: {_status}"
            f"\n📖 {texts['is_read_text']}: 📩 {_read}")

    await callback.message.edit_text(text=text, reply_markup=None)


async def support_write_new_message(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    text = await get_text("support_appeal_to_admin_text", language)

    await callback.answer()
    await callback.message.edit_text(text=text)
    await state.set_state(SupportState.writeToAdmin)


async def support_get_new_message_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if message.text:
        if message.text == "/cancelMessage":
            text = await get_text("support_get_writen_message_canceled", language)
            await message.answer(text=text)
        else:
            text = await get_text("support_get_writen_message_text", language)
            await message.answer(text=text)
            await utils.create_support_message(user.id, message.text)

        texts = await get_texts((
            "support_menu_text", 'appeal_to_admin_button',
            'add_category_button', 'testing_questions_file'
        ), language)

        markup = await inline_kb.support_menu_markup(texts)

        await message.answer(text=texts['support_menu_text'], reply_markup=markup)
        await state.update_data(markup_message_id=message.message_id + 1)
        await state.set_state(SupportState.support)
        return

    text = await get_text("support_get_writen_message_not_allowed", language)
    await message.answer(text=text)
    return


async def support_add_category_handler(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language if user.language else 'en'

    text = await get_text("support_add_category_text", language)
    await callback.message.edit_text(text=text, reply_markup=None)
    await state.set_state(SupportState.addCategoryTitle)
    await callback.answer()


async def support_add_category_title_handler(message: types.Message, state: FSMContext):
    user = await utils.get_user(message.from_user)
    language = user.language if user.language else 'en'

    if not message.text:
        text = await get_text("message_object_not_text", language)
        await message.answer(text=text)
        return

    if message.text == "/cancelCName":
        texts = await get_texts((
            "support_menu_text", 'appeal_to_admin_button',
            'add_category_button', 'testing_questions_file'
        ), language)
        markup = await inline_kb.support_menu_markup(texts)

        await message.answer(text=texts['support_menu_text'], reply_markup=markup)
        await state.update_data(markup_message_id=message.message_id + 1)
        await state.set_state(SupportState.support)
        return

    if len(message.text) > 60:
        text = await get_text("support_add_category_not_allowed_length_text", language)
        await message.answer(text=text)
        return

    new_category = await utils.create_pending_category(message.text)
    text = await get_text("support_add_category_new_category_saved_success", language, {
        "title": new_category.title if new_category else "",
    })

    texts = await get_texts((
        "support_menu_text", 'appeal_to_admin_button',
        'add_category_button', 'testing_questions_file'
    ), language)
    markup = await inline_kb.support_menu_markup(texts)
    await message.answer(text=text)
    await message.answer(text=texts['support_menu_text'], reply_markup=markup)
    await state.update_data(markup_message_id=message.message_id + 1)
    await state.set_state(SupportState.support)
    return


async def support_testing_questions_file_handler(callback: types.CallbackQuery, state: FSMContext):
    # user = await utils.get_user(callback.from_user)
    # language = user.language if user.language else 'en'

    return await callback.answer("This feature is not yet completed. 🚧🔧❌")

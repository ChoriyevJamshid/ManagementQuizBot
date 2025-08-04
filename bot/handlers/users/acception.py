from aiogram import types
from aiogram.fsm.context import FSMContext

from bot import utils
from bot.utils.functions import get_text, get_texts


async def add_user_to_quiz_allowed_callback(callback: types.CallbackQuery, state: FSMContext):
    user = await utils.get_user(callback.from_user)
    language = user.language or 'en'

    _, ans, request_chat_id, request_quiz_id = callback.data.split('_')

    quiz = await utils.get_quiz_by_id(quiz_id=int(request_quiz_id))
    if not quiz:
        text = await get_text('quiz_not_found', language)
        return await callback.answer(text, show_alert=True)

    answer_texts = await get_texts((
        'user_added_to_quiz_allowed_users', 'user_declined_to_join_quiz_allowed_users'
    ), language)


    if ans == "no":
        text = answer_texts['user_declined_to_join_quiz_allowed_users']
        answer_text = await get_text('user_not_allowed_by_owner', language, parameters={'title': quiz.title})
        await callback.bot.send_message(chat_id=request_chat_id, text=answer_text)
    else:
        text = answer_texts['user_added_to_quiz_allowed_users']
        answer_text = await get_text('user_allowed_by_owner', language, parameters={'title': quiz.title})

        quiz.allowed_users.append(request_chat_id)

    try:
        await callback.message.delete_reply_markup()
    except Exception as e:
        pass

    await callback.answer(text, show_alert=True)
    await callback.bot.send_message(chat_id=request_chat_id, text=answer_text)
    return await quiz.asave(update_fields=['allowed_users', 'updated_at'])




from aiogram import types
from django.conf import settings
from django.utils.timezone import now

from bot import utils
from bot.utils.functions import get_text
from quiz.tasks import group_quiz_create_file


async def send_excel_to_user_callback(callback: types.CallbackQuery):

    _, quiz_id, language = callback.data.split('_')

    group_quiz = await utils.get_group_quiz_for_excel(quiz_id)
    if not group_quiz:
        text = await get_text('group_quiz_not_found', language)
        return await callback.answer(text, show_alert=True)

    is_exists = await utils.check_user_exists(callback.from_user)
    if not is_exists:
        text = await get_text('subscribe_to_bot_before_get_statistics', language)
        return await callback.answer(text, show_alert=True)

    if not group_quiz.file:
        text = await get_text('group_quiz_no_file_please_wait', language)
        await callback.answer(text, show_alert=True)

        players = group_quiz.data.get('players', {})
        sorted_players = sorted(players.items(), key=lambda item: (-item[1]['corrects'], item[1]['spent_time']))
        quantity = group_quiz.part.quiz.quantity

        if group_quiz.part.quiz.quantity != group_quiz.index:
            quantity = group_quiz.index

        group_quiz_create_file.delay(
            file_path=f"{settings.BASE_DIR}/trush/{group_quiz.pk}.xlsx",
            sorted_players=sorted_players,
            quantity=quantity,
            quiz_id=group_quiz.pk,
        )
        return None


    file_path = group_quiz.file.path
    file_name = f"statistics_{now().date()}.xlsx"

    text = await get_text('statistics_file_sent', language)
    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=types.FSInputFile(file_path, filename=file_name)
    )
    await callback.answer(text, show_alert=True)
    return await callback.answer()








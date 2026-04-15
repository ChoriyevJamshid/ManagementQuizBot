import os
from aiogram import types
from django.conf import settings
from django.utils.timezone import now

from bot import utils
from bot.utils.functions import get_text
from quiz.tasks import group_quiz_create_file


async def send_excel_to_user_callback(callback: types.CallbackQuery):
    try:
        _, quiz_id = callback.data.split("_", 1)
    except (ValueError, AttributeError):
        return await callback.answer()

    group_quiz = await utils.get_group_quiz_for_excel(quiz_id)

    if not group_quiz:
        text = await get_text("group_quiz_not_found")
        return await callback.answer(text, show_alert=True)

    if not await utils.check_user_exists(callback.from_user):
        text = await get_text("subscribe_to_bot_before_get_statistics")
        return await callback.answer(text, show_alert=True)

    if not group_quiz.file:
        text = await get_text("group_quiz_no_file_please_wait")
        await callback.answer(text, show_alert=True)

        players = {}
        if isinstance(group_quiz.data, dict):
            players = group_quiz.data.get("players", {})

        if not players:
            return

        sorted_players = sorted(
            players.items(),
            key=lambda item: (-item[1]["corrects"], item[1]["spent_time"])
        )

        quantity = min(group_quiz.part.quiz.quantity, group_quiz.index)

        group_quiz_create_file.delay(
            file_path=f"{settings.BASE_DIR}/trush/{group_quiz.pk}.xlsx",
            sorted_players=sorted_players,
            quantity=quantity,
            quiz_id=group_quiz.pk,
        )
        return

    file_path = group_quiz.file.path

    if not os.path.exists(file_path):
        text = await get_text("group_quiz_no_file_please_wait")
        return await callback.answer(text, show_alert=True)

    file_name = f"statistics_{now().date()}.xlsx"

    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=types.FSInputFile(file_path, filename=file_name)
    )

    text = await get_text("statistics_file_sent")
    return await callback.answer(text, show_alert=True)

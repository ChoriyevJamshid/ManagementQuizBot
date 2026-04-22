import asyncio
import logging
import os

from aiogram import types
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.utils.timezone import now

from bot import utils
from bot.utils.functions import create_excel_statistics, get_text, sort_players

logger = logging.getLogger(__name__)


@sync_to_async
def _save_excel_to_server(group_quiz_pk: int, file_bytes: bytes) -> None:
    from quiz.models import GroupQuiz
    quiz = GroupQuiz.objects.filter(pk=group_quiz_pk).first()
    if quiz and not quiz.file:
        quiz.file.save("statistics.xlsx", ContentFile(file_bytes), save=False)
        quiz.save(update_fields=["file", "updated_at"])


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

    file_name = f"statistics_{now().date()}.xlsx"

    # Serve from server if the file is already saved
    if group_quiz.file:
        try:
            file_path = group_quiz.file.path
            if os.path.exists(file_path):
                await callback.bot.send_document(
                    chat_id=callback.from_user.id,
                    document=types.FSInputFile(file_path, filename=file_name),
                )
                text = await get_text("statistics_file_sent")
                return await callback.answer(text, show_alert=True)
        except Exception:
            logger.exception("Failed to serve statistics file for quiz %s", quiz_id)

    # File not on server yet — generate from saved player data
    players = group_quiz.data.get("players", {}) if isinstance(group_quiz.data, dict) else {}

    if not players:
        text = await get_text("group_quiz_no_file_please_wait")
        return await callback.answer(text, show_alert=True)

    quantity = group_quiz.index if group_quiz.index > 0 else group_quiz.part.quiz.quantity
    timer = group_quiz.part.quiz.timer
    sorted_players = sort_players(players, quantity, timer)

    file_bytes = await asyncio.to_thread(create_excel_statistics, sorted_players, quantity, timer)

    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=types.BufferedInputFile(file_bytes, filename=file_name),
    )
    text = await get_text("statistics_file_sent")
    await callback.answer(text, show_alert=True)

    asyncio.create_task(_save_excel_to_server(group_quiz.pk, file_bytes))

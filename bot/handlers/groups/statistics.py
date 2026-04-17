import os
import logging

from django.conf import settings
from aiogram import Bot

from quiz.choices import QuizStatus
from quiz.models import GroupQuiz

from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text, get_texts, reform_spent_time
from bot.utils import redis_group
from quiz.tasks import group_quiz_create_file

logger = logging.getLogger(__name__)


async def send_statistics(group_id: str, bot: Bot, is_cancelled: bool = False):

    def get_total_time(player):
        skips = max(0, quantity - player["corrects"] - player["wrongs"])
        return player["spent_time"] + (timer * skips)

    group_quiz = await utils.get_group_quiz_no_prefetch(group_id=group_id)
    if not group_quiz:
        return

    # Atomic guard: only ONE concurrent caller proceeds.
    # Prevents double-send when run_group_quiz_loop finishes at the same time
    # as stop_handler is called.
    new_status = QuizStatus.CANCELED if is_cancelled else QuizStatus.FINISHED
    updated = await GroupQuiz.objects.filter(
        pk=group_quiz.pk,
        status__in=[QuizStatus.STARTED, QuizStatus.INIT]
    ).aupdate(status=new_status)

    if not updated:
        return

    # Refresh to get the latest answers/index counts after all poll handlers complete.
    await group_quiz.arefresh_from_db(fields=["answers", "index"])

    players = await redis_group.get_all_players_data(str(group_quiz.pk))

    part = group_quiz.part
    quiz = part.quiz
    timer = quiz.timer
    quantity = group_quiz.index if group_quiz.index > 0 else quiz.quantity

    if not players:
        text = await get_text(
            "group_quiz_finished_noone_took_part",
            {"title": quiz.title}
        )
    else:

        sorted_players = sorted(
            players.items(),
            key=lambda item: (-int(item[1]["corrects"]), get_total_time(item[1]))
        )

        os.makedirs(f"{settings.BASE_DIR}/trush", exist_ok=True)

        group_quiz_create_file.delay(
            file_path=f"{settings.BASE_DIR}/trush/{group_quiz.pk}.xlsx",
            sorted_players=sorted_players,
            quantity=quantity,
            quiz_id=group_quiz.pk,
        )

        gifts = {1: "🥇", 2: "🥈", 3: "🥉"} # 4: "🏅"
        lines = []

        for index, (_, player) in enumerate(sorted_players[:50], start=1):
            username = player["username"]
            corrects = player["corrects"]
            wrongs = player["wrongs"]
            skips = max(0, quantity - corrects - wrongs)
            spent_time = player["spent_time"] + (timer * skips)
            formatted_time = reform_spent_time(spent_time)
            prefix = gifts.get(index, f"{index}.")
            lines.append(f"{prefix} {username} - {corrects} ({formatted_time})")

        users_text = "\n".join(lines)

        text = await get_text(
            "group_quiz_finished",
            {
                "title": part.title,
                "count": str(group_quiz.answers),
                "users": users_text,
            }
        )

    texts = await get_texts(("share_quiz_button", "get_excel_button"))
    markup = await inline_kb.test_group_share_quiz(
        texts=texts,
        link=part.link,
        group_quiz_id=group_quiz.pk,
    )

    try:
        await bot.send_message(chat_id=group_id, text=text, reply_markup=markup)
    except Exception:
        logger.exception("Failed to send statistics to group %s", group_id)

    if not isinstance(group_quiz.data, dict):
        group_quiz.data = {}

    if players:
        group_quiz.data["players"] = players

    group_quiz.participant_count = len(players) if players else 0

    try:
        await group_quiz.asave(
            update_fields=["data", "participant_count", "updated_at"]
        )
    except Exception:
        logger.exception("Failed to persist group_quiz %s after statistics", group_quiz.pk)

    await redis_group.delete_group_quiz_data(str(group_quiz.pk))

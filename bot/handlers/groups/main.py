import asyncio
import logging
from aiogram import types
from aiogram.enums import ChatMemberStatus

from quiz.choices import QuizStatus
from quiz.models import GroupQuiz

from bot import utils
from bot.utils.functions import get_text

from quiz.tasks import get_group_invite_link
from bot.utils import redis_group

from .common import get_creator, check_user_role
from .statistics import send_statistics
from .testing import start_group_testing

ACTIVE_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}

logger = logging.getLogger(__name__)


async def bot_group_member_updated(event: types.ChatMemberUpdated):
    new_status = event.new_chat_member.status

    if new_status in ACTIVE_STATUSES:
        try:
            admins = await event.bot.get_chat_administrators(event.chat.id)
        except Exception:
            logger.exception("bot_group_member_updated: failed to get admins for %s", event.chat.id)
            admins = []

        admin_tg_ids = [a.user.id for a in admins if not a.user.is_bot]
        privileged = await utils.get_privileged_profile_by_tg_ids(admin_tg_ids)

        await utils.add_or_update_telegram_group(
            telegram_id=event.chat.id,
            title=event.chat.title,
            username=getattr(event.chat, 'username', None),
            added_by_pk=privileged.pk if privileged else None,
        )
        logger.info("bot_group_member_updated: group %s added/updated in DB", event.chat.id)

    elif new_status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        await utils.deactivate_telegram_group(event.chat.id)
        logger.info("bot_group_member_updated: group %s deactivated in DB", event.chat.id)


async def group_title_updated(message: types.Message):
    await utils.update_telegram_group_title(
        telegram_id=message.chat.id,
        title=message.new_chat_title,
    )
    logger.info("group_title_updated: group %s title changed to %r", message.chat.id, message.new_chat_title)


async def send_quiz_ready_message(message, quiz_part):
    text = await get_text(
        "testing_group_quiz_part_ready_info",
        {
            "from_i": str(quiz_part.from_i),
            "to_i": str(quiz_part.to_i),
            "quantity": str(quiz_part.quantity),
            "timer": str(quiz_part.quiz.timer),
            "title": str(quiz_part.title),
        },
    )
    return await message.answer(text)


async def start_quiz_after_delay(group_id: str, bot):
    await asyncio.sleep(10)
    group_quiz = await utils.get_group_quiz(group_id)
    if not group_quiz or group_quiz.status != QuizStatus.INIT:
        return
    updated = await utils.update_group_quiz(group_quiz)
    if not updated:
        return
    await start_group_testing(group_quiz=group_quiz, bot=bot)


async def stop_handler(message: types.Message):
    group_id = str(message.chat.id)

    group_quiz = await utils.get_group_quiz_no_prefetch(group_id=group_id)

    if not group_quiz:
        text = await get_text("testing_not_active_quiz")
        return await message.answer(text)

    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id
        )
    except Exception:
        member = None

    is_owner = str(message.from_user.id) == group_quiz.user.chat_id

    is_admin = (
            member
            and member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}
    )

    is_channel_sender = (
            message.sender_chat
            and message.sender_chat.id == message.chat.id
    )

    if is_owner or is_admin or is_channel_sender:
        await redis_group.set_quiz_inactive(str(group_quiz.pk))
        return await send_statistics(
            group_quiz.group_id,
            message.bot,
            is_cancelled=True
        )

    text = await get_text("group_only_owner_can_stop_quiz")
    return await message.answer(text)


async def start_handler(message: types.Message):
    if not message.text:
        return

    parts = message.text.split()

    if len(parts) < 2:
        return

    link = parts[-1]

    tg_user = await get_creator(message) if message.from_user.is_bot else message.from_user

    if not tg_user:
        text = await get_text("group_make_bot_as_admin")
        return await message.answer(text)

    user = await utils.get_user(tg_user)

    quiz_part = await utils.get_quiz_part(link)
    if not quiz_part:
        return


    is_allowed = await check_user_role(user)
    if not is_allowed:
        text = await get_text("testing_not_allowed_role")
        return await message.answer(text)

    group_id = str(message.chat.id)
    group_quiz = await utils.get_group_quiz_no_prefetch(group_id=group_id)

    if not group_quiz:
        ready_msg = await send_quiz_ready_message(message, quiz_part)
        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=group_id,
            message_id=str(ready_msg.message_id),
            title=message.chat.title,
            invite_link=message.chat.invite_link,
        )
        starts_text = await get_text("group_quiz_starts_in_10_sec")
        await message.answer(starts_text)
        asyncio.create_task(start_quiz_after_delay(group_id, message.bot))
        return

    if group_quiz.status == QuizStatus.INIT:
        if quiz_part.id != group_quiz.part_id:
            group_quiz.part_id = quiz_part.id

        group_quiz.data = {}
        group_quiz.user = user

        ready_msg = await send_quiz_ready_message(message, quiz_part)
        group_quiz.message_id = str(ready_msg.message_id)

        await group_quiz.asave(
            update_fields=["message_id", "part_id", "data", "user"]
        )

        starts_text = await get_text("group_quiz_starts_in_10_sec")
        await message.answer(starts_text)
        asyncio.create_task(start_quiz_after_delay(group_id, message.bot))
        return

    # STARTED but not active in Redis → stale record (server restart or race condition).
    # Clean up silently and allow starting a fresh quiz.
    if not await redis_group.is_quiz_active(str(group_quiz.pk)):
        await GroupQuiz.objects.filter(
            pk=group_quiz.pk,
            status=QuizStatus.STARTED,
        ).aupdate(status=QuizStatus.CANCELED)
        await redis_group.delete_group_quiz_data(str(group_quiz.pk))
        ready_msg = await send_quiz_ready_message(message, quiz_part)
        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=group_id,
            message_id=str(ready_msg.message_id),
            title=message.chat.title,
            invite_link=message.chat.invite_link,
        )
        starts_text = await get_text("group_quiz_starts_in_10_sec")
        await message.answer(starts_text)
        asyncio.create_task(start_quiz_after_delay(group_id, message.bot))
        return

    text = await get_text(
        "testing_quiz_active_not_stopped",
        {"title": str(group_quiz.part.quiz.title)},
    )

    return await message.answer(text)



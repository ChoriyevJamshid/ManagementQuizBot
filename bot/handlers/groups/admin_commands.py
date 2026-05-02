import logging

from aiogram import types

from bot import utils
from bot.utils.functions import get_text

logger = logging.getLogger(__name__)


async def add_group_handler(message: types.Message):
    if message.chat.type not in ('group', 'supergroup'):
        text = await get_text('add_group_only_in_group')
        await message.answer(text)
        return

    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
    except Exception:
        logger.exception(
            "add_group: failed to get administrators for group_id=%s", message.chat.id,
        )
        await message.answer("⚠️ Xatolik yuz berdi.")
        return

    admin_tg_ids = [a.user.id for a in admins if not a.user.is_bot]
    logger.info(
        "add_group: group_id=%s has %d human admins: %s",
        message.chat.id, len(admin_tg_ids), admin_tg_ids,
    )

    privileged = await utils.get_privileged_profile_by_tg_ids(admin_tg_ids)
    if not privileged:
        logger.info(
            "add_group: no ADMIN/MODERATOR found among admins of group_id=%s — ignoring",
            message.chat.id,
        )
        return

    logger.info(
        "add_group: privileged user found chat_id=%s role=%s — adding group_id=%s",
        privileged.chat_id, privileged.role, message.chat.id,
    )

    try:
        group, created = await utils.add_or_update_telegram_group(
            telegram_id=message.chat.id,
            title=message.chat.title,
            username=message.chat.username,
            added_by_pk=privileged.pk,
        )
        key = 'add_group_added' if created else 'add_group_updated'
        text = await get_text(key, {'title': group.title})
        await message.answer(text)
        logger.info(
            "add_group: %s telegram_id=%s title=%r",
            'added' if created else 'updated', message.chat.id, group.title,
        )
    except Exception:
        logger.exception(
            "add_group: failed to upsert group telegram_id=%s", message.chat.id,
        )
        await message.answer("⚠️ Xatolik yuz berdi.")

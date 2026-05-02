import logging

from aiogram import types
from asgiref.sync import sync_to_async

from bot.utils import get_user
from bot.utils.functions import get_text
from utils.choices import Role

logger = logging.getLogger(__name__)


async def add_group_handler(message: types.Message):
    if message.chat.type not in ('group', 'supergroup'):
        text = await get_text('add_group_only_in_group')
        await message.answer(text)
        return

    user = await get_user(message.from_user)
    if user.role not in (Role.ADMIN, Role.MODERATOR):
        logger.info(
            "add_group: user_id=%s role=%s tried /add in group_id=%s — not privileged",
            message.from_user.id, user.role, message.chat.id,
        )
        return

    chat = message.chat

    def _upsert():
        from common.models import TelegramGroup
        obj, created = TelegramGroup.objects.update_or_create(
            telegram_id=chat.id,
            defaults={
                'title': chat.title or str(chat.id),
                'username': chat.username,
                'added_by_id': user.pk,
                'is_active': True,
            },
        )
        return obj, created

    try:
        group, created = await sync_to_async(_upsert)()
        key = 'add_group_added' if created else 'add_group_updated'
        text = await get_text(key, {'title': group.title})
        await message.answer(text)
        logger.info(
            "add_group: user_id=%s %s group telegram_id=%s title=%r",
            message.from_user.id, 'added' if created else 'updated',
            chat.id, chat.title,
        )
    except Exception:
        logger.exception(
            "add_group: user_id=%s failed to add group telegram_id=%s",
            message.from_user.id, chat.id,
        )
        await message.answer("⚠️ Xatolik yuz berdi.")

from aiogram import types
from aiogram.enums import ChatMemberStatus

from bot import utils


async def bot_added_to_channel_as_admin(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        await event.answer(
            f"Чат {event.chat.title} добавлен в базу данных"
        )
        return await utils.add_or_check_chat(event.chat.id)
    return await utils.remove_chat(event.chat.id)

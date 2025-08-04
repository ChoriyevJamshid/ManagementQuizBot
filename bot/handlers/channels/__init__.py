from aiogram import Router, F

from bot.filters import ChatTypeFilter
from bot.handlers.channels.main import bot_added_to_channel_as_admin


def prepare_router() -> Router:
    router = Router()
    router.my_chat_member.register(
        bot_added_to_channel_as_admin,
        ChatTypeFilter(chat_types=('channel',))
    )
    return router

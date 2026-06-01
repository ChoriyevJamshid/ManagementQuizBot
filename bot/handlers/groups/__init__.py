from aiogram import Router, F
from aiogram.filters import CommandStart, Command

from bot.filters import ChatTypeFilter
from bot.handlers.groups.main import *
from bot.handlers.groups.testing import *
from bot.handlers.groups.handle import *


def prepare_router() -> Router:
    router = Router()

    router.message.filter(ChatTypeFilter(("group", "supergroup")))

    router.my_chat_member.register(
        bot_group_member_updated,
        ChatTypeFilter(chat_types=("group", "supergroup")),
    )

    router.message.register(start_handler, CommandStart())
    router.message.register(stop_handler, Command("stop"))
    router.message.register(group_title_updated, F.new_chat_title)

    router.callback_query.register(
        send_excel_to_user_callback,
        F.data.startswith("testing-group-get-excel")
    )

    router.poll_answer.register(testing_group_poll_answer_handler)

    return router

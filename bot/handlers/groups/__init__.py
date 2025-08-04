from aiogram import Router, F
from aiogram.filters import CommandStart, Command, or_f

from bot.filters import ChatTypeFilter
from bot.handlers.groups.main import *
from bot.handlers.groups.testing import *
from bot.handlers.groups.handle import *

def prepare_router() -> Router:

    router = Router()
    router.message.filter(ChatTypeFilter(('group', 'supergroup')))

    router.message.register(start_handler, CommandStart())
    router.message.register(
        stop_handler,
        or_f(Command('stop'), Command('stopQuiz'),)
    )

    router.callback_query.register(
        send_excel_to_user_callback,
        F.data.startswith("testing-group-get-excel")
    )

    router.callback_query.register(
        get_ready_callback_handler,
        F.data.startswith('group-ready')
    )

    router.callback_query.register(
        testing_continue_callback_handler,
        F.data.startswith('testing-group-continue-quiz')
    )

    router.poll_answer.register(testing_group_poll_answer_handler)
    return router



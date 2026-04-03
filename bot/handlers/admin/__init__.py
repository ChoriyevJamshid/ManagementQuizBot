from aiogram import types, Router, F
from aiogram.filters import Command


from bot.handlers.admin.main import *


def prepare_router() -> Router:
    router = Router()

    router.message.register(
        admin_handler, Command('admin')
    )

    router.callback_query.register(
        admin_user_count_callback,
        F.data == "admin-users-count"
    )

    router.callback_query.register(
        admin_back_admin_menu_callback,
        F.data == "back-to-admin-menu"
    )

    return router

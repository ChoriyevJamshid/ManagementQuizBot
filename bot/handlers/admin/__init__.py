from aiogram import types, Router, F
from aiogram.filters import Command


from bot.handlers.admin.main import *


def prepare_router() -> Router:
    router = Router()


    router.message.register(
        get_admin_answer_to_pending_message_handler,
        MainState.admin_write
    )

    router.message.register(
        admin_handler, Command('admin')
    )

    router.callback_query.register(
        admin_user_count_callback,
        F.data == "admin-users-count"
    )

    router.callback_query.register(
        admin_support_messages_count_callback,
        F.data == "admin-support-messages-count"
    )

    router.callback_query.register(
        admin_support_pending_messages_callback,
        F.data == "admin-support-pending-messages"
    )

    router.callback_query.register(
        admin_pending_message_callback,
        F.data.startswith("admin-pending-message-check")
    )

    router.callback_query.register(
        admin_back_admin_menu_callback,
        F.data == "back-to-admin-menu"
    )

    return router

from typing import Awaitable, Callable, Any, Dict

# from aiogram import BaseMiddleware
# from aiogram.types import Update
#
# from bot import utils


# class RegisteredMiddleware(BaseMiddleware):
#
#     def __init__(self):
#         pass
#
#     async def __call__(
#             self,
#             handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
#             event: Update,
#             data: Dict[str, Any],
#     ):
#         telegram_user = None
#         if event.event_type == "message":
#             telegram_user = event.message.from_user
#         elif event.event_type == "callback_query":
#             telegram_user = event.callback_query.from_user
#
#         if telegram_user:
#             user = await utils.get_user(telegram_user)
#             if user and user.is_registered:
#
#
#
#
#         return await handler(event, data)






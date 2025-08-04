from typing import Callable, Awaitable, Union, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Update

from bot import utils
from utils import Role



class CheckingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        if not event.message and not event.callback_query:
            return await handler(event, data)
        if event.message:
            tg_user = event.message.from_user
        else:
            tg_user = event.callback_query.from_user

        if tg_user.is_bot:
            return await handler(event, data)

        user = await utils.get_user(tg_user)
        if user.role == Role.ADMIN:
            return await handler(event, data)

        return None





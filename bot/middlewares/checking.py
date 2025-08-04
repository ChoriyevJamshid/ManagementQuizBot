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

        user = await utils.get_user(event)
        if user.role == Role.ADMIN:
            return await handler(event, data)

        return None





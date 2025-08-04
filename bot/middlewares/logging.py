from typing import Callable, Awaitable, Dict, Any
from aiogram import types, BaseMiddleware


class LoggingMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: types.Update,
            data: Dict[str, Any],
    ):
        return await handler(event, data)





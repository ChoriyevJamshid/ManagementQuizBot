import time
import logging
from typing import Callable, Awaitable, Dict, Any
from aiogram import types, BaseMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: types.Update,
            data: Dict[str, Any],
    ):
        start_time = time.time()
        try:
            return await handler(event, data)
        finally:
            execution_time = time.time() - start_time

            handler_obj = data.get("handler")
            handler_name = "Unknown"
            if handler_obj and hasattr(handler_obj, "callback"):
                 handler_name = handler_obj.callback.__name__

            logger.info("Handler '%s' executed in %.4f seconds", handler_name, execution_time)

            # Anonymous/channel-authored group messages have no from_user.
            from_user = getattr(event, "from_user", None)
            if from_user:
                logger.info("User: %s - %s", from_user.full_name, from_user.id)

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

            print(f"Handler '{handler_name}' executed in {execution_time:.4f} seconds")
            print(f"User: {event.from_user.full_name} - {event.from_user.id}")
            
            logging.info(f"Handler '{handler_name}' executed in {execution_time:.4f} seconds")
            logging.info(f"User: {event.from_user.full_name} - {event.from_user.id}")

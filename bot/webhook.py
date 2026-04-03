import logging

import orjson
from aiohttp import ClientTimeout

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder

from redis.asyncio import Redis, ConnectionPool

from src.settings import API_TOKEN, REDIS_HOST, REDIS_PORT

from bot import handlers, middlewares


logger = logging.getLogger(__name__)


def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(handlers.admin.prepare_router())
    dp.include_router(handlers.users.prepare_router())
    dp.include_router(handlers.groups.prepare_router())


def setup_middlewares(dp: Dispatcher) -> None:
    dp.message.middleware(middlewares.LoggingMiddleware())
    dp.callback_query.middleware(middlewares.LoggingMiddleware())


def _build_bot() -> Bot:
    session = AiohttpSession(
        json_loads=orjson.loads,
        timeout=ClientTimeout(total=30, connect=10),
    )
    return Bot(
        token=API_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _build_storage() -> RedisStorage:
    pool = ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=2,
        max_connections=50,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    redis = Redis(connection_pool=pool)
    return RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(prefix="fsm"),
    )


class WebhookService:
    """
    Telegram webhook processor.
    Production-ready singleton — created once at Django startup.
    """

    def __init__(self) -> None:
        self.bot = _build_bot()
        self.dp = Dispatcher(storage=_build_storage())
        setup_handlers(self.dp)
        setup_middlewares(self.dp)
        logger.info("WebhookService initialised")

    async def process_update(self, body: bytes) -> None:
        try:
            update = Update.model_validate_json(body)
            await self.dp.feed_update(bot=self.bot, update=update)
        except Exception:
            logger.exception("Failed to process update")

    async def shutdown(self) -> None:
        logger.info("WebhookService shutting down")
        await self.bot.session.close()
        await self.dp.storage.close()


webhook = WebhookService()

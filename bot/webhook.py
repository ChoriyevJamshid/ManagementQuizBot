import logging
import orjson

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
    # dp.message.middleware(middlewares.CheckingMiddleware())
    # dp.callback_query.middleware(middlewares.CheckingMiddleware())


class WebhookService:
    """
    Telegram webhook processor
    Production ready version
    """

    def __init__(self) -> None:

        session = AiohttpSession(json_loads=orjson.loads)

        self.bot = Bot(
            token=API_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        pool = ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=2,
            max_connections=10,
            decode_responses=False
        )

        redis = Redis(connection_pool=pool)

        storage = RedisStorage(
            redis=redis,
            key_builder=DefaultKeyBuilder(prefix="fsm")
        )

        self.dp = Dispatcher(storage=storage)

        setup_handlers(self.dp)
        setup_middlewares(self.dp)

        logger.info("Telegram webhook initialized")

    async def process_update(self, body: bytes) -> None:
        """
        Process incoming telegram update
        """

        try:
            update = Update.model_validate_json(body)

            await self.dp.feed_update(
                bot=self.bot,
                update=update
            )

        except Exception:
            logger.exception("Failed to process telegram update")

    async def shutdown(self):
        """
        Graceful shutdown
        """

        logger.info("Shutting down telegram bot")

        await self.bot.session.close()


webhook = WebhookService()
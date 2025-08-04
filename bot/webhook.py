import logging
import orjson

from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.client import Redis

from src.settings import API_TOKEN, REDIS_HOST, REDIS_PORT
from bot import handlers, middlewares

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(handlers.admin.prepare_router())
    dp.include_router(handlers.users.prepare_router())
    dp.include_router(handlers.groups.prepare_router())


def setup_middlewares(dp: Dispatcher) -> None:
    # dp.update.middleware(middlewares.LoggingMiddleware())
    pass

class Webhook:
    def __init__(self) -> None:
        self.is_setup = False

        self.bot = Bot(
            token=API_TOKEN,
            session=AiohttpSession(json_loads=orjson.loads),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        _redis = Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=2
        )
        key_builder = DefaultKeyBuilder(prefix="fsm_state")
        storage = RedisStorage(
            redis=_redis,
            key_builder=key_builder,
        )
        self.dp = Dispatcher(storage=storage)


    def setup_webhook(self):
        if not self.is_setup:
            setup_handlers(self.dp)
            setup_middlewares(self.dp)
            self.is_setup = True

    async def process(self, request):
        return await self._process_update(request)

    async def _process_update(self, request):
        update = types.Update.model_validate_json(request.body.decode("utf-8"))
        await self.dp.feed_update(bot=self.bot, update=update)

    async def process_body(self, body: str):
        try:
            update = types.Update.model_validate_json(body)
            await self.dp.feed_update(bot=self.bot, update=update)
        except Exception as e:
            logging.error(f"Webhook processing error: {e}")

webhook = Webhook()
webhook.setup_webhook()
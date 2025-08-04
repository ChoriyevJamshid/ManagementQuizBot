import logging
import orjson
import asyncio

from django.conf import settings

from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(handlers.admin.prepare_router())
    dp.include_router(handlers.channels.prepare_router())
    dp.include_router(handlers.groups.prepare_router())
    dp.include_router(handlers.users.prepare_router())



def setup_middlewares(dp: Dispatcher) -> None:
    pass


async def setup_aiogram(dp: Dispatcher) -> None:
    setup_handlers(dp)
    setup_middlewares(dp)


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await setup_aiogram(dispatcher)
    await bot.delete_webhook(drop_pending_updates=True)


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.session.close()
    await dispatcher.storage.close()

def main() -> None:
    bot = Bot(
        token=settings.API_TOKEN,
        session=AiohttpSession(json_loads=orjson.loads),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.startup.register(aiogram_on_startup_polling)
    dp.shutdown.register(aiogram_on_shutdown_polling)
    asyncio.run(dp.start_polling(bot, allowed_updates=[
        "message", "edited_message", "channel_post", "edited_channel_post",
        "inline_query", "chosen_inline_result", "callback_query",
        "shipping_query", "pre_checkout_query", "poll", "poll_answer",
        "chat_member", "my_chat_member", "chat_join_request"
    ]))



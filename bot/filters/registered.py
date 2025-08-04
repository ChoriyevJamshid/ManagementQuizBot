from typing import Any, Callable, Dict, Awaitable, Union

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext

from bot.utils import get_user
from bot.keyboards import reply_kb
from bot.utils.functions import get_texts
from bot.states import MainState


class RegisteredFilter(Filter):

    def __init__(self):
        pass

    async def __call__(self, event: Message | CallbackQuery, state: FSMContext) -> bool:
        message = None
        if isinstance(event, Message):
            message = event
        elif isinstance(event, CallbackQuery):
            message = event.message

        if message:
            user = await get_user(message.from_user)
            if user.language is None \
                    or user.is_registered \
                    or message.content_type == ContentType.CONTACT:
                return True

            language = user.language or 'en'
            texts = await get_texts(
                ('user_share_contact_for_register_text', 'share_contact_text'), language
            )
            try:
                await message.delete_reply_markup()
            except Exception:
                pass

            await message.answer(
                text=texts['user_share_contact_for_register_text'],
                reply_markup=await reply_kb.share_contact_markup(text=texts['share_contact_text'])
            )
            await state.set_state(MainState.share_contact)

            if isinstance(event, CallbackQuery):
                await event.answer()
            return False
        return True

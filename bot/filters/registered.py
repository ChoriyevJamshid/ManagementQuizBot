from typing import Any, Callable, Dict, Awaitable, Union

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext

from bot.utils import get_user
from bot.keyboards import reply_kb
from bot.utils.functions import get_texts
from bot.states import MainState
from utils import Role


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
            user = await get_user(event.from_user)
            current_state = await state.get_state()

            if user.role not in (Role.ADMIN, Role.MODERATOR):
                return False
            
            if user.is_registered \
                    or message.content_type == ContentType.CONTACT:
                return True
                
            if isinstance(event, Message) and current_state == MainState.share_contact.state:
                return True

            texts = await get_texts(
                ('user_share_contact_for_register_text', 'share_contact_text')
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
            return True
        return True

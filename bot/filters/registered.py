from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext

from bot.utils import get_user
from bot.keyboards import reply_kb
from bot.utils.functions import get_texts, get_text
from bot.states import MainState
from utils.choices import Role


class RegisteredFilter(Filter):

    async def __call__(self, event: Message | CallbackQuery, state: FSMContext) -> bool:
        if isinstance(event, CallbackQuery):
            message = event.message
        elif isinstance(event, Message):
            message = event
        else:
            return True

        user = await get_user(event.from_user)

        if user.is_registered:
            if user.role in (Role.ADMIN, Role.MODERATOR):
                return True
            text = await get_text('not_allowed_role_global')
            await message.answer(text=text)
            if isinstance(event, CallbackQuery):
                await event.answer()
            return False

        # Пользователь отправляет контакт — пропускаем (обработчик сам сохранит)
        if isinstance(event, Message) and event.content_type == ContentType.CONTACT:
            return True

        # Уже в состоянии ожидания контакта — пропускаем
        current_state = await state.get_state()
        if current_state == MainState.share_contact.state:
            return True

        # Незарегистрированный — просим поделиться контактом
        texts = await get_texts(('user_share_contact_for_register_text', 'share_contact_text'))
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

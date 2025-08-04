import typing

from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import states, utils
from bot.utils.functions import get_text


class CancelFilter(Filter):
    def __init__(self, function: typing.Callable) -> None:
        super().__init__()
        self.function = function

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        if len(message.text.split(' ')) == 2:
            await self.function(message, state)
            return False



        current_state = await state.get_state()
        data = await state.get_data()

        if current_state == states.QuizState.testing:
            user = await utils.get_user(message.chat)
            data = await state.get_data()
            if not data:
                data = {}
            language = user.language if user.language else 'uz'
            text = await get_text("testing_quiz_active_not_stopped", language, {
                "title": data.get('current_user_quiz', {}).get("title", "QUIZ")
            })
            await message.answer(text)
            return False

        message_id = message.message_id - 1
        if data.get('markup_message_id', None) is not None:
            message_id = data.get('markup_message_id', 1)
            await state.clear()

        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=message_id,
                reply_markup=None
            )
        except Exception as e:
            print(f"\nError: {e}\n")

        return True


class ChatTypeFilter(Filter):
    def     __init__(self, chat_types: tuple) -> None:
        super().__init__()
        self.chat_types = chat_types

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        return message.chat.type in self.chat_types


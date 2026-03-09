import asyncio
from aiogram import types
from bot.utils.functions import get_texts, get_text

from utils import Role


async def delete_quiz_reply_markup(group_id: str, message_id: str, callback: types.CallbackQuery):
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=group_id,
            message_id=message_id,
            reply_markup=None
        )
    except Exception:
        pass


async def animate_texts(group_id: str, callback: types.CallbackQuery):
    texts = await get_texts(
        ('group_test_is_starting', 'animate_5', 'animate_4', 'animate_3', 'animate_2', 'animate_1', 'animate_go')
    )
    text_keys = list(texts.keys())
    text_keys.remove('group_test_is_starting')

    await asyncio.sleep(1)
    msg = await callback.bot.send_message(
        chat_id=group_id,
        text=texts['group_test_is_starting'],
    )
    await asyncio.sleep(1)

    for key in text_keys:
        await asyncio.sleep(1)
        try:
            await callback.bot.edit_message_text(
                chat_id=group_id,
                message_id=msg.message_id,
                text=texts[key],
            )
        except:
            msg = await callback.bot.send_message(
                chat_id=group_id,
                text=texts[key],
            )
    return msg.message_id


async def get_creator(message: types.Message) -> types.User | None:
    user = None
    admins = await message.bot.get_chat_administrators(chat_id=message.chat.id)
    for admin in admins:
        if isinstance(admin, types.ChatMemberOwner):
            user = admin.user
            break
    return user


async def check_user_role(
        user,
        message
):
    if user.role not in [Role.ADMIN, Role.MODERATOR]:
        text = await get_text('testing_not_allowed_role')
        await message.answer(text)
        return False
    return True



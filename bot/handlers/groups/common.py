import asyncio
from aiogram import types, Bot
from bot.utils.functions import get_texts, get_text

from utils import Role


async def delete_quiz_reply_markup(group_id: str, message_id: int | str, bot: Bot):
    try:
        await bot.edit_message_reply_markup(
            chat_id=group_id,
            message_id=message_id,
            reply_markup=None
        )
    except Exception:
        pass


async def animate_texts(group_id: str, bot: Bot):
    # 3-2-1-GO: total ~3 seconds instead of 7
    texts = await get_texts(
        ('group_test_is_starting', 'animate_3', 'animate_2', 'animate_1', 'animate_go')
    )
    text_keys = list(texts.keys())
    text_keys.remove('group_test_is_starting')

    msg = await bot.send_message(
        chat_id=group_id,
        text=texts['group_test_is_starting'],
    )

    for key in text_keys:
        await asyncio.sleep(0.75)
        try:
            await bot.edit_message_text(
                chat_id=group_id,
                message_id=msg.message_id,
                text=texts[key],
            )
        except Exception:
            msg = await bot.send_message(
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


async def check_user_role(user):
    if user.role not in [Role.ADMIN, Role.MODERATOR]:
        return False
    return True



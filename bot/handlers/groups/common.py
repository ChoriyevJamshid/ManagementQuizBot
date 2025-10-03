import asyncio
from aiogram import types

from bot.utils import texts
from quiz.tasks import send_notify_to_quiz_owner
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

    text = texts.group_test_is_starting
    text_list = [
        texts.animate_5,
        texts.animate_4,
        texts.animate_3,
        texts.animate_2,
        texts.animate_1,
        texts.animate_go
    ]

    await asyncio.sleep(1)
    msg = await callback.bot.send_message(
        chat_id=group_id,
        text=text,
    )
    await asyncio.sleep(1)

    for text in text_list:
        await asyncio.sleep(1)
        try:
            await callback.bot.edit_message_text(
                chat_id=group_id,
                message_id=msg.message_id,
                text=text,
            )
        except:
            msg = await callback.bot.send_message(
                chat_id=group_id,
                text=text,
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


async def check_quiz_part_owner(
        quiz_part,
        user,
        message,
):
    if user.role != Role.ADMIN:
        if user.phone_number:
            user_cred = user.phone_number
        elif user.username:
            user_cred = f"@{user.username}"
        else:
            user_cred = user.first_name
            if user.last_name:
                user_cred += " " + user.last_name

        group_cred = f"@{message.chat.username}" if message.chat.username else message.chat.title
        text = texts.testing_group_quiz_is_private

        await message.answer(text)
        send_notify_to_quiz_owner.delay(
            quiz_id=quiz_part.quiz.id,
            group_credential=group_cred,
            user_credential=user_cred,
            user_chat_id=user.chat_id
        )
        return False
    return True



import asyncio
from aiogram import types
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.context import FSMContext

from quiz.choices import QuizStatus

from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text

from quiz.tasks import get_group_invite_link
from bot.utils import redis_group

from .common import get_creator, check_user_role
from .statistics import send_statistics
from .testing import start_group_testing


async def send_quiz_ready_message(message, quiz_part):
    text = await get_text(
        "testing_group_quiz_part_ready_info",
        {
            "from_i": str(quiz_part.from_i),
            "to_i": str(quiz_part.to_i),
            "quantity": str(quiz_part.quantity),
            "timer": str(quiz_part.quiz.timer),
            "title": str(quiz_part.title),
        },
    )

    markup = await inline_kb.group_ready_markup(str(message.chat.id))

    return await message.answer(text, reply_markup=markup)


async def start_quiz_after_delay(group_quiz, bot, state: FSMContext):
    print("QUIZ WILL START IN 10s")
    await asyncio.sleep(10)
    print("STARTING QUIZ")
    await start_group_testing(
        group_quiz=group_quiz,
        bot=bot,
        state=state
    )


async def stop_handler(message: types.Message):
    group_id = str(message.chat.id)

    group_quiz = await utils.get_group_quiz(group_id=group_id)

    if not group_quiz:
        text = await get_text("testing_not_active_quiz")
        return await message.answer(text)

    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id
        )
    except Exception:
        member = None

    is_owner = str(message.from_user.id) == group_quiz.user.chat_id

    is_admin = (
            member
            and member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}
    )

    is_channel_sender = (
            message.sender_chat
            and message.sender_chat.id == message.chat.id
    )

    if is_owner or is_admin or is_channel_sender:
        return await send_statistics(
            group_quiz.group_id,
            message.bot,
            is_cancelled=True
        )

    text = await get_text("group_only_owner_can_stop_quiz")

    return await message.answer(text)


async def start_handler(message: types.Message):
    if not message.text:
        return

    parts = message.text.split()

    if len(parts) < 2:
        return

    link = parts[-1]

    tg_user = await get_creator(message) if message.from_user.is_bot else message.from_user

    if not tg_user:
        text = await get_text("group_make_bot_as_admin", "uz")
        return await message.answer(text)

    user = await utils.get_user(tg_user)

    quiz_part = await utils.get_quiz_part(link)

    if not quiz_part:
        # TODO: text quiz not found
        return

    group_id = str(message.chat.id)

    group_quiz = await utils.get_group_quiz(group_id=group_id)

    is_allowed = await check_user_role(user)

    if not is_allowed:
        text = await get_text("testing_not_allowed_role")
        return await message.answer(text)

    if not group_quiz:
        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=group_id,
            message_id=str(message.message_id + 1),
            title=message.chat.title,
            invite_link=message.chat.invite_link,
        )

        return await send_quiz_ready_message(message, quiz_part)

    if group_quiz.status == QuizStatus.INIT:

        try:
            await message.bot.edit_message_reply_markup(
                chat_id=group_quiz.group_id,
                message_id=group_quiz.message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        if quiz_part.id != group_quiz.part_id:
            group_quiz.part_id = quiz_part.id

        group_quiz.data = {}
        group_quiz.message_id = str(message.message_id + 1)
        group_quiz.user = user

        await group_quiz.asave(
            update_fields=["message_id", "part_id", "data", "user"]
        )

        return await send_quiz_ready_message(message, quiz_part)

    text = await get_text(
        "testing_quiz_active_not_stopped",
        {"title": str(group_quiz.part.quiz.title)},
    )

    return await message.answer(text)


async def get_ready_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    group_quiz = await utils.get_group_quiz(group_id=str(callback.message.chat.id))

    if not group_quiz:
        return await callback.answer()

    user = callback.from_user

    username = (
        f"@{user.username}"
        if user.username
        else f"{user.first_name} {user.last_name or ''}".strip()
    )

    # атомарно добавляем игрока
    await redis_group.add_player_to_group_quiz(
        group_quiz_id=str(group_quiz.pk),
        user_id=str(user.id),
        username=username
    )

    players_count = await redis_group.get_players_count(str(group_quiz.pk))

    text = await get_text(
        "testing_group_quiz_part_ready_info_with_ready_counter",
        {
            "from_i": str(group_quiz.part.from_i),
            "to_i": str(group_quiz.part.to_i),
            "quantity": str(group_quiz.part.quantity),
            "timer": str(group_quiz.part.quiz.timer),
            "title": str(group_quiz.part.title),
            "count": str(players_count),
        },
    )

    callback_text = await get_text("group_test_starts_soon")

    markup = await inline_kb.group_ready_markup(str(callback.message.chat.id))

    try:
        await callback.bot.edit_message_text(
            chat_id=group_quiz.group_id,
            message_id=group_quiz.message_id,
            text=text,
            reply_markup=markup,
        )
    except Exception:
        pass

    await callback.answer(callback_text)

    # atomic start
    if players_count >= 2:

        updated = await utils.update_group_quiz(group_quiz)
        print(f"\n{updated = }\n")
        if updated:
            print(f"working updated")
            asyncio.create_task(
                start_quiz_after_delay(
                    group_quiz,
                    callback.bot,
                    state
                )
            )

    if not group_quiz.invite_link:
        get_group_invite_link.delay(group_quiz.pk)

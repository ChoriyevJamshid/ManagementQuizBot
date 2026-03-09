import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext

from quiz.choices import QuizStatus

from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text

from quiz.tasks import get_group_invite_link
from .statistics import send_statistics
from .testing import testing_send_tests_by_recurse
from .common import get_creator, check_user_role
from bot.utils import redis_group


async def stop_handler(message: types.Message):
    group_quiz = await utils.get_group_quiz(str(message.chat.id))
    member = await message.bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
    if group_quiz is None:
        text = await get_text('testing_not_active_quiz')
        return message.answer(text)

    if (group_quiz.user.chat_id == str(message.from_user.id)) \
            or member in (types.ChatMemberOwner, types.ChatMemberAdministrator) \
            or (message.sender_chat and message.chat.id == message.sender_chat.id):
        return await send_statistics(group_quiz.group_id, message.bot, is_cancelled=True)

    text = await get_text('group_only_owner_can_stop_quiz', )
    return await message.answer(text)


async def start_handler(message: types.Message):
    if message.from_user.is_bot:
        tg_user = await get_creator(message)
    else:
        tg_user = message.from_user

    if not tg_user:
        text = await get_text("group_make_bot_as_admin", 'uz')
        return await message.answer(text)

    user = await utils.get_user(tg_user)
    if len(message.text.split(' ')) == 1:
        return None

    link = message.text.split(' ')[-1]
    if not await utils.exists_quiz_part(link):
        return None

    group_quiz = await utils.get_group_quiz(group_id=str(message.chat.id))

    if group_quiz is None:
        quiz_part = await utils.get_quiz_part(link)

        is_allowed = await check_user_role(user, message)

        print(f"\n{is_allowed = }\n")
        if not is_allowed:
            return None
            # group_cred = message.chat.username or message.chat.title
            # user_cred = user.username or user.phone_number or user.first_name
            # text = await get_text('testing_group_quiz_is_private')
            #
            # await message.answer(text)
            # return send_notify_to_quiz_owner.delay(
            #     quiz_id=quiz_part.quiz.id,
            #     group_credential=group_cred,
            #     user_credential=user_cred,
            #     user_chat_id=user.chat_id
            # )

        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=str(message.chat.id),
            message_id=str(message.message_id + 1),
            title=message.chat.title,
            invite_link=message.chat.invite_link,
             
        )

        text = await get_text(
            'testing_group_quiz_part_ready_info',
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.title),
            }
        )
        markup = await inline_kb.group_ready_markup(str(message.chat.id))
        return await message.answer(text, reply_markup=markup)

    if group_quiz.status == QuizStatus.INIT:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=group_quiz.group_id,
                message_id=group_quiz.message_id,
                reply_markup=None
            )
        except:
            pass

        quiz_part = await utils.get_quiz_part(link)
        if quiz_part.id != group_quiz.part_id:
            group_quiz.part_id = quiz_part.id

        is_allowed = await check_user_role(user, message)
        if not is_allowed:
            return None

        group_quiz.data = dict()
        group_quiz.message_id = str(message.message_id + 1)
        group_quiz.user = user

        text = await get_text(
            'testing_group_quiz_part_ready_info',
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.title),
            }
        )

        markup = await inline_kb.group_ready_markup(str(message.chat.id))
        await message.answer(text, reply_markup=markup)
        return await group_quiz.asave(update_fields=['message_id', 'part_id', 'data', 'user'])


    text = await get_text('testing_quiz_active_not_stopped', {
        'title': str(group_quiz.part.quiz.title)
    })
    return await message.answer(text)


async def get_ready_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    group_quiz = await utils.get_group_quiz(group_id=str(callback.message.chat.id))

    if group_quiz is None:
        return await callback.answer()

    if callback.from_user.is_bot:
        return await callback.answer()

    if callback.from_user.username:
        username = "@" + callback.from_user.username
    else:
        username = callback.from_user.first_name
        if callback.from_user.last_name:
            username += " " + callback.from_user.last_name

    # Atomically add the player to Redis (if they aren't already there)
    await redis_group.add_player_to_group_quiz(
        group_quiz_id=str(group_quiz.pk),
        user_id=str(callback.from_user.id),
        username=username
    )
    
    # Get total count directly from Redis Hash length
    players_count = await redis_group.get_players_count(str(group_quiz.pk))

    text = await get_text(
        'testing_group_quiz_part_ready_info_with_ready_counter',
        {
            "from_i": str(group_quiz.part.from_i),
            "to_i": str(group_quiz.part.to_i),
            "quantity": str(group_quiz.part.quantity),
            "timer": str(group_quiz.part.quiz.timer),
            "title": str(group_quiz.part.title),
            "count": str(players_count),
        }
    )
    callback_text = await get_text('group_test_starts_soon')
    markup = await inline_kb.group_ready_markup(str(callback.message.chat.id))

    try:
        await callback.bot.edit_message_text(
            chat_id=group_quiz.group_id,
            message_id=group_quiz.message_id,
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        pass

    await callback.answer(callback_text)
    
    if group_quiz.status == QuizStatus.INIT and players_count >= 2:
        group_quiz.status = QuizStatus.STARTED
        await group_quiz.asave(update_fields=['status'])

        await asyncio.sleep(10)
        return await testing_send_tests_by_recurse(group_quiz, callback, state)

    if not group_quiz.invite_link:
        get_group_invite_link.delay(group_quiz.pk)




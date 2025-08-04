import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext

from quiz.choices import QuizStatus

from bot import utils
from bot.keyboards import inline_kb
from bot.utils.functions import get_text

from quiz.tasks import (
    get_group_invite_link,
    send_notify_to_quiz_owner
)
from .statistics import send_statistics
from .testing import testing_send_tests_by_recurse
from .common import get_creator, check_quiz_part_owner


async def stop_handler(message: types.Message):
    group_quiz = await utils.get_group_quiz(str(message.chat.id))
    member = await message.bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
    language = group_quiz.language or "en"
    if group_quiz is None:
        text = await get_text('testing_not_active_quiz', language)
        return message.answer(text)

    if (group_quiz.user.chat_id == str(message.from_user.id)) \
            or member in (types.ChatMemberOwner, types.ChatMemberAdministrator) \
            or (message.sender_chat and message.chat.id == message.sender_chat.id):
        return await send_statistics(group_quiz.group_id, message.bot, is_cancelled=True)

    text = await get_text('group_only_owner_can_stop_quiz', language, )
    return await message.answer(text)


async def start_handler(message: types.Message):
    if message.from_user.is_bot:
        tg_user = await get_creator(message)
    else:
        tg_user = message.from_user

    if not tg_user:
        text = await get_text("group_make_bot_as_admin", 'en')
        return await message.answer(text)

    user = await utils.get_user(tg_user)
    if len(message.text.split(' ')) == 1:
        return None

    language = user.language or "en"
    link = message.text.split(' ')[-1]
    if not await utils.exists_quiz_part(link):
        return None

    group_quiz = await utils.get_group_quiz(group_id=str(message.chat.id))

    if group_quiz is None:
        quiz_part = await utils.get_quiz_part(link)

        print(f"\n{quiz_part.quiz.privacy is True = }\n")
        print(f"\n{user.chat_id != quiz_part.quiz.owner.chat_id = }\n")
        print(f"\n{user.chat_id not in quiz_part.quiz.allowed_users = }\n")
        print(f"{quiz_part.quiz.allowed_users = }")

        is_owner = await check_quiz_part_owner(quiz_part, user, message, language)
        if not is_owner:
            return None
        if (
                quiz_part.quiz.privacy is True
                and user.chat_id != quiz_part.quiz.owner.chat_id
                and user.chat_id not in quiz_part.quiz.allowed_users
        ):
            group_cred = message.chat.username or message.chat.title
            user_cred = user.username or user.phone_number or user.first_name
            text = await get_text('testing_group_quiz_is_private', language)

            await message.answer(text)
            return send_notify_to_quiz_owner.delay(
                quiz_id=quiz_part.quiz.id,
                group_credential=group_cred,
                user_credential=user_cred,
                user_chat_id=user.chat_id
            )

        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=str(message.chat.id),
            message_id=str(message.message_id + 1),
            title=message.chat.title,
            invite_link=message.chat.invite_link,
            language=language
        )

        text = await get_text(
            'testing_group_quiz_part_ready_info', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.title),
            }
        )
        markup = await inline_kb.group_ready_markup(str(message.chat.id), language)
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

        is_owner = await check_quiz_part_owner(quiz_part, user, message, language)
        if not is_owner:
            return None

        group_quiz.data = dict()
        group_quiz.message_id = str(message.message_id + 1)
        group_quiz.user = user

        text = await get_text(
            'testing_group_quiz_part_ready_info', language,
            {
                "from_i": str(quiz_part.from_i),
                "to_i": str(quiz_part.to_i),
                "quantity": str(quiz_part.quantity),
                "timer": str(quiz_part.quiz.timer),
                "title": str(quiz_part.title),
            }
        )

        markup = await inline_kb.group_ready_markup(str(message.chat.id), language)
        await message.answer(text, reply_markup=markup)
        return await group_quiz.asave(update_fields=['message_id', 'part_id', 'data', 'user'])


    text = await get_text('testing_quiz_active_not_stopped', language, {
        'title': str(group_quiz.part.quiz.title)
    })
    return await message.answer(text)


async def get_ready_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    group_quiz = await utils.get_group_quiz(group_id=str(callback.message.chat.id))
    language = group_quiz.language or "en"

    if group_quiz is None:
        return await callback.answer()

    if callback.from_user.is_bot:
        return await callback.answer()

    players_data = group_quiz.data.get('players', {})
    if players_data.get(str(callback.from_user.id)):
        return await callback.answer()

    if callback.from_user.username:
        username = "@" + callback.from_user.username
    else:
        username = callback.from_user.first_name
        if callback.from_user.last_name:
            username += " " + callback.from_user.last_name

    players_data[str(callback.from_user.id)] = {
        'corrects': 0,
        'wrongs': 0,
        'spent_time': 0,
        'username': username,
    }

    text = await get_text(
        'testing_group_quiz_part_ready_info_with_ready_counter',
        language,
        {
            "from_i": str(group_quiz.part.from_i),
            "to_i": str(group_quiz.part.to_i),
            "quantity": str(group_quiz.part.quantity),
            "timer": str(group_quiz.part.quiz.timer),
            "title": str(group_quiz.part.title),
            "count": str(len(players_data.keys())),
        }
    )
    callback_text = await get_text('group_test_starts_soon', language)
    markup = await inline_kb.group_ready_markup(str(callback.message.chat.id), language)

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
    if group_quiz.status == QuizStatus.INIT and len(players_data) >= 2:
        group_quiz.status = QuizStatus.STARTED
        group_quiz.data['players'] = players_data
        await group_quiz.asave(update_fields=['data', 'status'])

        await asyncio.sleep(10)
        return await testing_send_tests_by_recurse(group_quiz, callback, state)

    if not group_quiz.invite_link:
        get_group_invite_link.delay(group_quiz.pk)
    group_quiz.data['players'] = players_data
    return await group_quiz.asave(update_fields=['data', 'status'])




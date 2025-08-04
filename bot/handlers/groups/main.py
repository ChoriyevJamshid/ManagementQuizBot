import time
import asyncio

from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from quiz.choices import QuizStatus
from quiz.models import GroupQuiz

from bot import utils
from bot.keyboards import inline_kb
from bot.states import QuizState
from bot.utils.functions import (
    get_text,
    get_texts,
    generate_user_quiz_data,
    reform_spent_time
)
from quiz.tasks import get_group_invite_link


async def get_creator(message: types.Message) -> types.User | None:
    user  = None
    admins = await message.bot.get_chat_administrators(chat_id=message.chat.id)
    for admin in admins:
        if isinstance(admin, types.ChatMemberOwner):
            user = admin.user
            break
    return user


async def delete_quiz_reply_markup(group_id: str, message_id: str, callback: types.CallbackQuery):
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=group_id,
            message_id=message_id,
            reply_markup=None
        )
    except Exception:
        pass


async def animate_texts(group_id: str, callback: types.CallbackQuery,  language: str = "en"):
    texts = await get_texts(
        ('group_test_is_starting', 'animate_5', 'animate_4', 'animate_3', 'animate_2', 'animate_1', 'animate_go'),
        language=language
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


async def send_tests_by_recurse(
        group_id: str,
        index: int,
        question_data: dict,
        poll_question: str,
        timer: int,
        callback: types.CallbackQuery,
        state: FSMContext
):
    total_questions = len(question_data)

    if index >= total_questions:
        return await send_statistics(group_id, callback.bot)

    group_quiz = await utils.get_group_quiz(group_id)
    if not group_quiz:
        return None

    language = group_quiz.language or "en"
    if index != 0 and not group_quiz.is_answered:
        group_quiz.skips += 1
        await group_quiz.asave(update_fields=['skips'])

    if group_quiz.is_answered:
        group_quiz.is_answered = False
        await group_quiz.asave(update_fields=['is_answered'])

    if group_quiz.skips == 2:
        group_quiz.skips = 0
        await group_quiz.asave(update_fields=['skips'])

        text = await get_text('group_noone_answer_to_questions', language)
        markup = await inline_kb.test_group_continue_markup(group_id, index, language)

        return await callback.bot.send_message(
            chat_id=group_id,
            text=text,
            reply_markup=markup,
        )

    question_text = (f"<b>[{index + 1}/{total_questions}]. {question_data[index]['question']}</b>\n\n"
                     f"<b>A)</b> <i>{question_data[index]['options'][0]}</i>\n"
                     f"<b>B)</b> <i>{question_data[index]['options'][1]}</i>\n"
                     f"<b>C)</b> <i>{question_data[index]['options'][2]}</i>\n"
                     f"<b>D)</b> <i>{question_data[index]['options'][3]}</i>\n")
    correct_option_id = question_data[index]['options'].index(question_data[index]['correct_option'])

    await callback.bot.send_message(chat_id=group_quiz.group_id, text=question_text)
    poll = await callback.bot.send_poll(
        chat_id=group_quiz.group_id,
        question=poll_question,
        options=['A', 'B', 'C', 'D'],
        is_anonymous=False,
        type='quiz',
        correct_option_id=correct_option_id,
        open_period=timer,
        protect_content=True
    )

    group_quiz.poll_id = poll.poll.id
    group_quiz.index = index + 1
    group_quiz.data['start_time'] = time.perf_counter()
    group_quiz.data['correct_option_id'] = correct_option_id
    await group_quiz.asave(update_fields=['poll_id', 'index', 'data'])

    await asyncio.sleep(timer + 2)
    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=index + 1,
        question_data=question_data,
        poll_question=poll_question,
        timer=timer,
        callback=callback,
        state=state
    )


async def send_statistics(group_id: str, bot: Bot, is_cancelled=False):
    players = None

    group_quiz = await utils.get_group_quiz(group_id=group_id)
    if not group_quiz:
        return None

    language = group_quiz.language or "en"
    if group_quiz.answers == 0:
        text = await get_text('group_quiz_finished_noone_took_part', language, {
            "title": group_quiz.part.quiz.title
        })
    else:
        players = group_quiz.data.get('players', {})
        sorted_players = sorted(players.items(), key=lambda item: (-item[1]['corrects'], item[1]['spent_time']))
        quantity = group_quiz.part.quiz.quantity

        if group_quiz.part.quiz.quantity != group_quiz.index:
            quantity = group_quiz.index

        users_text = str()
        for index, player_tuple in enumerate(sorted_players[:30], start=1):
            username = player_tuple[-1]['username']
            corrects = player_tuple[-1]['corrects']
            wrongs = player_tuple[-1]['wrongs']
            spent_time = player_tuple[-1]['spent_time']
            skips = quantity - corrects - wrongs
            spent_time += group_quiz.part.quiz.timer * skips
            formatted_spent_time = await reform_spent_time(spent_time)

            users_text += f"{index}. {username} - {corrects} ({formatted_spent_time})\n"

        text = await get_text('group_quiz_finished', language, {
            "title": group_quiz.part.quiz.title,
            "count": str(group_quiz.answers),
            "users": str(users_text),

        })

    markup = await inline_kb.test_group_share_quiz(link=group_quiz.part.link)
    await bot.send_message(chat_id=group_id, text=text, reply_markup=markup)

    group_quiz.status = QuizStatus.CANCELED if is_cancelled else QuizStatus.FINISHED
    if players:
        group_quiz.participant_count = len(players)
    return await group_quiz.asave(update_fields=['participant_count', 'status', 'updated_at'])


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
       user = await get_creator(message)
    else:
        user = message.from_user

    if not user:
        text = await get_text("group_make_bot_as_admin", 'en')
        return await message.answer(text)

    language = user.language or "en"
    user = await utils.get_user(user)
    if len(message.text.split(' ')) == 1:
        return None

    link = message.text.split(' ')[-1]
    if not await utils.exists_quiz_part(link):
        return None

    group_quiz = await utils.get_group_quiz(group_id=str(message.chat.id))

    if group_quiz is None:
        quiz_part = await utils.get_quiz_part(link)
        await utils.create_group_quiz(
            part_id=quiz_part.id,
            user_id=user.id,
            group_id=str(message.chat.id),
            message_id=str(message.message_id + 1),
            title = message.chat.title,
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
                "title": str(quiz_part.quiz.title),
            }
        )
        markup = await inline_kb.group_ready_markup(str(message.chat.id), language)
        await message.answer(text, reply_markup=markup)

    else:
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
                    "title": str(quiz_part.quiz.title),
                }
            )

            markup = await inline_kb.group_ready_markup(str(message.chat.id), language)
            await message.answer(text, reply_markup=markup)
            await group_quiz.asave(update_fields=['message_id', 'part_id', 'data', 'user'])
        else:
            text = await get_text('testing_quiz_active_not_stopped', language, {
                'title': str(group_quiz.part.quiz.title)
            })
            await message.answer(text)
    return None


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
            "title": str(group_quiz.part.quiz.title),
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

    get_group_invite_link.delay(group_quiz.pk)
    group_quiz.data['players'] = players_data
    return await group_quiz.asave(update_fields=['data', 'status'])


async def testing_send_tests_by_recurse(group_quiz: GroupQuiz, callback: types.CallbackQuery, state: FSMContext):

    language = group_quiz.language or "en"
    await delete_quiz_reply_markup(group_quiz.group_id, group_quiz.message_id, callback)
    message_id = await animate_texts(group_quiz.group_id, callback, language=language)

    await callback.bot.delete_message(chat_id=group_quiz.group_id, message_id=message_id)
    await state.set_state(QuizState.group_testing)

    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question', language)

    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=0,
        question_data=question_data,
        poll_question=poll_question,
        timer=group_quiz.part.quiz.timer,
        callback=callback,
        state=state
    )


async def testing_continue_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    _, group_id, index = callback.data.split('_')
    group_quiz = await utils.get_group_quiz(group_id)

    if not group_quiz:
        return await callback.answer()

    language = group_quiz.language or "en"
    question_data = await generate_user_quiz_data(group_quiz.part)
    poll_question = await get_text('poll_question', language)

    await callback.message.delete_reply_markup()
    await callback.answer()

    return await send_tests_by_recurse(
        group_id=group_quiz.group_id,
        index=int(index),
        question_data=question_data,
        poll_question=poll_question,
        timer=group_quiz.part.quiz.timer,
        callback=callback,
        state=state
    )


async def testing_group_poll_answer_handler(poll_answer: types.PollAnswer):
    end_time = time.perf_counter()
    group_quiz = await utils.get_group_quiz_by_poll_id(poll_answer.poll_id)

    if not group_quiz:
        return

    if not group_quiz.is_answered:
        group_quiz.is_answered = True
        group_quiz.answers += 1

    players_data = group_quiz.data.get('players', {})
    user_id = str(poll_answer.user.id)
    if poll_answer.voter_chat:
        user_id = str(poll_answer.voter_chat.id)

    user_data = players_data.get(user_id, None)
    if poll_answer.user.username:
        username = "@" + poll_answer.user.username
    else:
        username = poll_answer.user.first_name

    if not user_data:
        user_data = {
            'corrects': 0,
            'wrongs': 0,
            'spent_time': 0,
            'username': username
        }

    if poll_answer.option_ids[0] == group_quiz.data.get('correct_option_id', 10):
        user_data['corrects'] += 1
    else:
        user_data['wrongs'] += 1

    user_data['spent_time'] += round(end_time - group_quiz.data.get('start_time', 0), 1)
    players_data[user_id] = user_data
    group_quiz.data['players'] = players_data
    await group_quiz.asave(update_fields=['data', 'is_answered', 'answers'])

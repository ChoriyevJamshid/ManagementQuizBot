import os

from django.conf import settings
from aiogram import Bot

from quiz.choices import QuizStatus

from bot import utils
from bot.keyboards import inline_kb

from bot.utils.functions import (
    get_text,
    get_texts,
    reform_spent_time
)
from bot.utils import redis_group
from quiz.tasks import group_quiz_create_file



async def send_statistics(group_id: str, bot: Bot, is_cancelled=False):
    players = None

    group_quiz = await utils.get_group_quiz(group_id=group_id)
    if not group_quiz:
        return None

    # Pull final results directly from fast memory
    players = await redis_group.get_all_players_data(str(group_quiz.pk))

    if not players:
        text = await get_text('group_quiz_finished_noone_took_part', {
            "title": group_quiz.part.quiz.title
        })
    else:
        users_text = str()
        
        sorted_players = sorted(players.items(), key=lambda item: (-item[1]['corrects'], item[1]['spent_time']))
        quantity = group_quiz.part.quiz.quantity

        if group_quiz.part.quiz.quantity != group_quiz.index:
            quantity = group_quiz.index

        os.makedirs(f"{settings.BASE_DIR}/trush", exist_ok=True)
        group_quiz_create_file.delay(
            file_path=f"{settings.BASE_DIR}/trush/{group_quiz.pk}.xlsx",
            sorted_players=sorted_players,
            quantity=quantity,
            quiz_id=group_quiz.pk,
        )
        gifts = ("🏆", "🏅", "🎖", "🏵", "🎗")
        for index, player_tuple in enumerate(sorted_players[:50], start=1):

            username = player_tuple[-1]['username']
            corrects = player_tuple[-1]['corrects']
            wrongs = player_tuple[-1]['wrongs']
            spent_time = player_tuple[-1]['spent_time']
            skips = quantity - corrects - wrongs
            spent_time += group_quiz.part.quiz.timer * skips
            formatted_spent_time = reform_spent_time(spent_time)

            if index == 1:
                users_text += f"{gifts[0]}. {username} - {corrects} ({formatted_spent_time})\n"
            elif index == 2:
                users_text += f"{gifts[1]}. {username} - {corrects} ({formatted_spent_time})\n"
            elif index == 3:
                users_text += f"{gifts[2]}. {username} - {corrects} ({formatted_spent_time})\n"
            elif index == 4:
                users_text += f"{gifts[3]}. {username} - {corrects} ({formatted_spent_time})\n"
            elif index == 5:
                users_text += f"{gifts[4]}. {username} - {corrects} ({formatted_spent_time})\n"
            else:
                users_text += f"{index}. {username} - {corrects} ({formatted_spent_time})\n"

        text = await get_text('group_quiz_finished', {
            "title": group_quiz.part.title,
            "count": str(group_quiz.answers),
            "users": str(users_text),

        })

    texts = await get_texts(('share_quiz_button', 'get_excel_button'))
    markup = await inline_kb.test_group_share_quiz(
        texts=texts,
        link=group_quiz.part.link,
        group_quiz_id=group_quiz.pk,
         
    )
    await bot.send_message(chat_id=group_id, text=text, reply_markup=markup)

    # Permanently archive the results into PostgreSQL and clean up Redis!
    if not isinstance(group_quiz.data, dict):
        group_quiz.data = {}
        
    if players:
        group_quiz.data['players'] = players
        
    group_quiz.status = QuizStatus.CANCELED if is_cancelled else QuizStatus.FINISHED
    group_quiz.participant_count = len(players) if players else 0
    await group_quiz.asave(update_fields=['data', 'participant_count', 'status', 'updated_at'])
    
    # Wipe Redis clean since test is over
    await redis_group.delete_group_quiz_data(group_quiz_id=str(group_quiz.pk))
    return


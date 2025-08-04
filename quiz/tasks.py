import os
from celery import shared_task
from django.conf import settings
from quiz.models import GroupQuiz, Quiz

from bot.utils.methods import get_chat, send_text
from bot.utils.functions import create_excel_statistics, get_texts_sync, get_text_sync


@shared_task
def get_group_invite_link(pk: int):

    group = GroupQuiz.objects.filter(pk=pk).first()
    if group is None:
        return None

    response = get_chat(chat_id=int(group.group_id))
    if response.status_code == 200:
        data = response.json()
        group.invite_link = data.get('result', {}).get('invite_link')
        group.save(update_fields=['invite_link'])
        return group.invite_link

    return None


@shared_task
def group_quiz_create_file(
        quiz_id: int,
        file_path: str,
        sorted_players: list | tuple, quantity: int
):
    quiz  = GroupQuiz.objects.filter(pk=quiz_id).first()
    language = quiz.language or 'en'
    if not quiz:
        return None

    if quiz.file:
        print(f"File exists for quiz {quiz_id}")
        return None


    create_excel_statistics(
        file_path=file_path,
        sorted_players=sorted_players,
        quantity=quantity,
        language=language
    )

    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            quiz.file.save("statistics.xlsx", file)
            quiz.save(update_fields=['file', 'updated_at'])
        os.remove(file_path)
    else:
        print(f"File {file_path} not found")

    return None


@shared_task
def send_notify_to_quiz_owner(
        quiz_id: int,
        user_chat_id: int,
        group_credential: str,
        user_credential: str,
):
    quiz = Quiz.objects.filter(id=quiz_id).select_related('owner').first()
    if not quiz:
        return None

    telegram_id = quiz.owner.chat_id
    language = quiz.owner.language or 'en'

    text = get_text_sync(
        code='send_notify_to_quiz_owner',
        language=language,
        parameters={
            'quizname': quiz.title,
            'username': user_credential,
            'groupname': group_credential
        })

    btn_texts = get_texts_sync((
        'accept_user_button', 'decline_user_button'
    ), language)
    a_text = btn_texts['accept_user_button']
    d_text = btn_texts['decline_user_button']

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": f"{a_text}", "callback_data": f"accept-user-to-use-quiz_yes_{user_chat_id}_{quiz_id}"},
                {"text": f"{d_text}", "callback_data": f"accept-user-to-use-quiz_no_{user_chat_id}_{quiz_id}"}
            ],
        ]
    }

    send_text(chat_id=telegram_id, text=text, reply_markup=reply_markup)
    return None



@shared_task
def remove_quiz_files():
    base_dir = settings.MEDIA_ROOT
    files = os.listdir(base_dir)

    for file in files:
        extension = file.split(".")[-1]
        if extension in ("xlsx", "xls", "doc", "docx", "txt"):
            if os.path.exists(f"{base_dir}/{file}"):
                os.remove(f"{base_dir}/{file}")

    return None




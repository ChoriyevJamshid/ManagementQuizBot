import os
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
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
        sorted_players: list | tuple,
        quantity: int,
        timer: int = 0,
):
    quiz = GroupQuiz.objects.filter(pk=quiz_id).first()
    if not quiz:
        return None

    if quiz.file:
        return None

    file_bytes = create_excel_statistics(
        sorted_players=sorted_players,
        quantity=quantity,
        timer=timer,
    )

    quiz.file.save("statistics.xlsx", ContentFile(file_bytes), save=False)
    quiz.save(update_fields=['file', 'updated_at'])

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




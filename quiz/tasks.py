import os
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from quiz.models import GroupQuiz, Quiz

from bot.utils.methods import get_chat, send_text
from bot.utils.functions import create_excel_statistics, get_texts_sync, get_text_sync
from quiz.choices import QuizStatus


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


@shared_task
def run_scheduled_quiz(scheduled_quiz_id: int):
    from quiz.models import ScheduledQuiz

    scheduled = ScheduledQuiz.objects.filter(pk=scheduled_quiz_id, is_active=True).first()
    if not scheduled:
        return

    text = get_text_sync('schedule_notify_1h')
    send_text(chat_id=int(scheduled.group_id), text=text)

    notify_before_quiz.apply_async(
        kwargs={"scheduled_quiz_id": scheduled_quiz_id, "minutes_left": 10},
        countdown=50 * 60,
    )
    notify_before_quiz.apply_async(
        kwargs={"scheduled_quiz_id": scheduled_quiz_id, "minutes_left": 5},
        countdown=55 * 60,
    )
    start_scheduled_group_quiz.apply_async(
        kwargs={"scheduled_quiz_id": scheduled_quiz_id},
        countdown=60 * 60,
    )


@shared_task
def notify_before_quiz(scheduled_quiz_id: int, minutes_left: int):
    from quiz.models import ScheduledQuiz

    scheduled = ScheduledQuiz.objects.filter(pk=scheduled_quiz_id, is_active=True).first()
    if not scheduled:
        return

    key = 'schedule_notify_10m' if minutes_left == 10 else 'schedule_notify_5m'
    text = get_text_sync(key)
    send_text(chat_id=int(scheduled.group_id), text=text)


@shared_task
def start_scheduled_group_quiz(scheduled_quiz_id: int):
    from quiz.models import ScheduledQuiz

    scheduled = (
        ScheduledQuiz.objects
        .filter(pk=scheduled_quiz_id, is_active=True)
        .select_related('quiz_part', 'quiz_part__quiz', 'created_by')
        .first()
    )
    if not scheduled:
        return

    existing = GroupQuiz.objects.filter(
        group_id=scheduled.group_id
    ).exclude(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]).first()
    if existing:
        return

    quiz_part = scheduled.quiz_part
    ready_button_text = get_text_sync('testing_ready_button')
    reply_markup = {
        "inline_keyboard": [[
            {
                "text": ready_button_text,
                "callback_data": f"group-ready_{scheduled.group_id}",
            }
        ]]
    }

    text = get_text_sync('testing_group_quiz_part_ready_info', {
        "from_i": str(quiz_part.from_i),
        "to_i": str(quiz_part.to_i),
        "quantity": str(quiz_part.quantity),
        "timer": str(quiz_part.quiz.timer),
        "title": str(quiz_part.title or quiz_part.quiz.title),
    })

    response = send_text(
        chat_id=int(scheduled.group_id),
        text=text,
        reply_markup=reply_markup,
    )
    if response.status_code != 200:
        return

    message_id = str(response.json()['result']['message_id'])

    GroupQuiz.objects.create(
        part=quiz_part,
        user=scheduled.created_by,
        group_id=scheduled.group_id,
        message_id=message_id,
        title=scheduled.group_title or '',
        invite_link='',
    )

    if not scheduled.is_periodic:
        scheduled.is_active = False
        scheduled.save(update_fields=['is_active', 'updated_at'])
        if scheduled.periodic_task_id:
            from django_celery_beat.models import PeriodicTask
            PeriodicTask.objects.filter(pk=scheduled.periodic_task_id).update(enabled=False)




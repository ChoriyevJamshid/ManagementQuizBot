from aiogram import types

from django.db import models

from common import models as com_models
from quiz import models as quiz_models
from quiz.choices import QuizStatus
from quiz.models import GroupQuiz


async def get_users_count():
    return com_models.TelegramProfile.objects.aggregate(
        count=models.Count('id'),
    )['count']



async def get_data_solo():
    return com_models.Data.get_solo()


async def check_user_exists(chat: types.User):
    return await com_models.TelegramProfile.objects.filter(chat_id=chat.id).aexists()


async def get_user(chat: types.Chat | types.User, message=None, callback=None):
    user = await com_models.TelegramProfile.objects.filter(chat_id=chat.id).afirst()
    if not user:
        user = await com_models.TelegramProfile.objects.acreate(
            chat_id=chat.id,
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
        )
    return user


async def get_languages():
    return com_models.Language.objects.all()



async def get_user_quizzes(user_id: int):
    return quiz_models.Quiz.objects.filter(owner_id=user_id).values('id', 'title').order_by('-created_at')



async def get_quiz_by_id(quiz_id: int):
    return quiz_models.Quiz.objects.filter(id=quiz_id).select_related('owner', 'category').first()


async def get_quiz_values(quiz_id: int, values: list | tuple):
    return quiz_models.Quiz.objects.filter(id=quiz_id).values(*values).first()


async def get_quiz_parts(quiz_id: int):
    return quiz_models.QuizPart.objects.filter(quiz_id=quiz_id).select_related("quiz", "quiz__owner")


async def get_quiz_part(link: str):
    return await (
        quiz_models.QuizPart.objects
        .filter(link=link)
        .select_related("quiz", "quiz__owner")
        .afirst()
    )


async def get_exists_user_active_quiz(user_id: int):
    user_quiz = await quiz_models.UserQuiz.objects.filter(
        user_id=user_id, active=True
    ).select_related('part', 'part__quiz').afirst()

    if not user_quiz:
        return None
    return user_quiz.part.quiz.title


async def get_quiz_part_by_id(part_id: int):
    return await quiz_models.QuizPart.objects.filter(
        id=part_id
    ).prefetch_related(
        "questions", "questions__options"
    ).select_related("quiz", "quiz__owner").afirst()


async def create_user_quiz(part_id: int, user_id: int):
    return await quiz_models.UserQuiz.objects.acreate(
        part_id=part_id,
        user_id=user_id,
    )


async def get_user_active_quiz(user_id: int):
    return await quiz_models.UserQuiz.objects.filter(
        user_id=user_id, active=True
    ).select_related("part", "user", "part__quiz").afirst()


async def get_user_quizzes_count(part_id: int):
    return quiz_models.UserQuiz.objects.filter(part_id=part_id).count()



# queries for group

async def exists_quiz_part(link: str):
    return await quiz_models.QuizPart.objects.filter(link=link).aexists()


async def get_group_quiz(group_id: str) -> quiz_models.GroupQuiz | None:
    group_quiz = await quiz_models.GroupQuiz.objects.filter(
        ~models.Q(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]) & models.Q(group_id=group_id),
    ).prefetch_related(
        "part__questions", "part__questions__options"
    ).select_related('part', 'part__quiz', 'user').order_by('-id').afirst()
    return group_quiz


async def get_group_quiz_no_prefetch(group_id: str) -> quiz_models.GroupQuiz | None:
    """Lightweight fetch — no question prefetch. Use when questions are not needed."""
    return await quiz_models.GroupQuiz.objects.filter(
        ~models.Q(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]) & models.Q(group_id=group_id),
    ).select_related('part', 'part__quiz', 'user').order_by('-id').afirst()


async def get_group_quiz_by_poll_id(poll_id: str) -> quiz_models.GroupQuiz | None:
    return await quiz_models.GroupQuiz.objects.filter(
        ~models.Q(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]) & models.Q(poll_id=poll_id),
    ).prefetch_related(
        "part__questions", "part__questions__options"
    ).select_related('part', 'part__quiz', 'user').afirst()


async def get_group_quiz_for_excel(group_id: int | str) -> quiz_models.GroupQuiz | None:
    return await quiz_models.GroupQuiz.objects.filter(id=group_id).select_related(
        'part', 'part__quiz', 'user'
    ).afirst()


async def create_group_quiz(
        part_id: int,
        user_id: int,
        group_id: str,
        message_id: str,
        title: str,
        invite_link: str,
):
    return await quiz_models.GroupQuiz.objects.acreate(
        part_id=part_id,
        user_id=user_id,
        group_id=group_id,
        message_id=message_id,
        title=title,
        invite_link=invite_link,
    )


async def update_group_quiz(group_quiz):
    return await GroupQuiz.objects.filter(
        pk=group_quiz.pk,
        status=QuizStatus.INIT
    ).aupdate(status=QuizStatus.STARTED)



async def get_distinct_groups(limit: int = 10) -> list:
    from asgiref.sync import sync_to_async

    def _inner():
        seen = {}
        qs = quiz_models.GroupQuiz.objects.values('group_id', 'title').order_by('-created_at')[:limit * 5]
        for gq in qs:
            gid = gq['group_id']
            if gid not in seen:
                seen[gid] = gq.get('title') or gid
            if len(seen) >= limit:
                break
        return [{'group_id': k, 'title': v} for k, v in seen.items()]

    return await sync_to_async(_inner)()


async def create_scheduled_quiz(
    quiz_part_id: int,
    created_by_id: int,
    group_id: str,
    group_title: str,
    is_periodic: bool,
    hour: int,
    minute: int,
    days_of_week: str,
    start_date,
):
    from asgiref.sync import sync_to_async

    def _inner():
        import json
        import pytz
        from datetime import datetime, timedelta
        from django_celery_beat.models import CrontabSchedule, ClockedSchedule, PeriodicTask
        from quiz.models import ScheduledQuiz

        scheduled = ScheduledQuiz.objects.create(
            quiz_part_id=quiz_part_id,
            created_by_id=created_by_id,
            group_id=group_id,
            group_title=group_title,
            is_periodic=is_periodic,
            hour=hour,
            minute=minute,
            days_of_week=days_of_week,
            start_date=start_date,
        )

        task_hour = hour - 1 if hour > 0 else 23
        task_day = days_of_week

        # If quiz is at 00:xx, task runs at 23:xx previous day → shift days back by 1
        if hour == 0 and is_periodic and task_day != '*':
            days = [int(d) for d in task_day.split(',')]
            shifted = [(d - 1) % 7 for d in days]
            task_day = ','.join(map(str, sorted(shifted)))

        task_kwargs = json.dumps({"scheduled_quiz_id": scheduled.pk})
        task_name = f"scheduled_quiz_{scheduled.pk}"

        if is_periodic:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=str(minute),
                hour=str(task_hour),
                day_of_week=task_day,
                day_of_month='*',
                month_of_year='*',
                timezone='Asia/Tashkent',
            )
            periodic_task = PeriodicTask.objects.create(
                crontab=schedule,
                name=task_name,
                task='quiz.tasks.run_scheduled_quiz',
                kwargs=task_kwargs,
                enabled=True,
            )
        else:
            tz = pytz.timezone('Asia/Tashkent')
            quiz_dt = tz.localize(datetime(
                start_date.year, start_date.month, start_date.day,
                hour, minute,
            ))
            task_dt_utc = (quiz_dt - timedelta(hours=1)).astimezone(pytz.UTC).replace(tzinfo=None)
            clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=task_dt_utc)
            periodic_task = PeriodicTask.objects.create(
                clocked=clocked,
                name=task_name,
                task='quiz.tasks.run_scheduled_quiz',
                kwargs=task_kwargs,
                enabled=True,
                one_off=True,
            )

        scheduled.periodic_task = periodic_task
        scheduled.save(update_fields=['periodic_task'])
        return scheduled

    return await sync_to_async(_inner)()


async def add_or_check_chat(chat_id: int):
    data_obj = com_models.Data.get_solo()
    data_obj.channel_id = chat_id
    await data_obj.asave(update_fields=['channel_id'])


async def remove_chat(chat_id: int):
    data_obj = com_models.Data.get_solo()
    if data_obj.channel_id == chat_id:
        data_obj.channel_id = None
        await data_obj.asave(update_fields=['channel_id'])

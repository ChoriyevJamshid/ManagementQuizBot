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



async def get_privileged_profile_by_tg_ids(tg_ids: list) -> 'com_models.TelegramProfile | None':
    """Returns first TelegramProfile with ADMIN/MODERATOR role whose chat_id is in tg_ids."""
    from asgiref.sync import sync_to_async
    from utils.choices import Role as _Role

    def _inner():
        return com_models.TelegramProfile.objects.filter(
            chat_id__in=[str(i) for i in tg_ids],
            role__in=[_Role.ADMIN, _Role.MODERATOR],
        ).first()

    return await sync_to_async(_inner)()


async def add_or_update_telegram_group(
    telegram_id: int,
    title: str,
    username: str | None,
    added_by_pk: int | None,
) -> tuple:
    """Upsert TelegramGroup by telegram_id. Returns (group, created)."""
    from asgiref.sync import sync_to_async
    from common.models import TelegramGroup

    def _inner():
        return TelegramGroup.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'title': title or str(telegram_id),
                'username': username,
                'added_by_id': added_by_pk,
                'is_active': True,
            },
        )

    return await sync_to_async(_inner)()


async def deactivate_telegram_group(telegram_id: int) -> None:
    from asgiref.sync import sync_to_async
    from common.models import TelegramGroup

    await sync_to_async(
        lambda: TelegramGroup.objects.filter(telegram_id=telegram_id).update(is_active=False)
    )()


async def get_telegram_groups() -> list:
    from asgiref.sync import sync_to_async
    from common.models import TelegramGroup

    def _inner():
        groups = TelegramGroup.objects.filter(is_active=True).order_by('title')
        return [
            {
                'group_id': str(g.telegram_id),
                'title': g.title,
                'username': g.username,
            }
            for g in groups
        ]

    return await sync_to_async(_inner)()


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


async def get_all_quiz_parts() -> list:
    from asgiref.sync import sync_to_async

    def _inner():
        parts = (
            quiz_models.QuizPart.objects
            .select_related('quiz')
            .order_by('quiz__title', 'from_i')
        )
        return [
            {
                'id': p.id,
                'quiz_id': p.quiz.id,
                'quiz_title': p.quiz.title,
                'from_i': p.from_i,
                'to_i': p.to_i,
            }
            for p in parts
        ]

    return await sync_to_async(_inner)()


async def get_active_scheduled_sessions() -> list:
    from asgiref.sync import sync_to_async
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    def _inner():
        sessions = (
            ScheduledSession.objects
            .filter(status__in=[SessionStatus.PENDING, SessionStatus.RUNNING])
            .select_related('created_by')
            .order_by('scheduled_at')
        )
        return list(sessions)

    return await sync_to_async(_inner)()


async def create_scheduled_session(
    created_by_id: int,
    group_id: str,
    group_title: str,
    part_ids: list,
    scheduled_at,
) -> 'quiz_models.ScheduledSession':
    from asgiref.sync import sync_to_async

    def _inner():
        import pytz
        from datetime import datetime, timedelta, timezone as dt_timezone
        from quiz.models import ScheduledSession
        from quiz.choices import SessionStatus
        from quiz.tasks import notify_scheduled_session, start_scheduled_session

        now = datetime.now(dt_timezone.utc)
        delta_seconds = (scheduled_at - now).total_seconds()

        session = ScheduledSession.objects.create(
            created_by_id=created_by_id,
            group_id=group_id,
            group_title=group_title,
            part_ids=part_ids,
            scheduled_at=scheduled_at,
            status=SessionStatus.PENDING,
        )

        task_ids = []

        if delta_seconds > 60 * 60:
            t = notify_scheduled_session.apply_async(
                kwargs={"session_id": session.pk, "label": "1h"},
                eta=scheduled_at - timedelta(hours=1),
            )
            task_ids.append(t.id)

        if delta_seconds > 10 * 60:
            t = notify_scheduled_session.apply_async(
                kwargs={"session_id": session.pk, "label": "10m"},
                eta=scheduled_at - timedelta(minutes=10),
            )
            task_ids.append(t.id)

        if delta_seconds > 5 * 60:
            t = notify_scheduled_session.apply_async(
                kwargs={"session_id": session.pk, "label": "5m"},
                eta=scheduled_at - timedelta(minutes=5),
            )
            task_ids.append(t.id)

        t = start_scheduled_session.apply_async(
            kwargs={"session_id": session.pk},
            eta=scheduled_at,
        )
        task_ids.append(t.id)

        session.celery_task_ids = task_ids
        session.save(update_fields=['celery_task_ids'])
        return session

    return await sync_to_async(_inner)()


async def cancel_scheduled_session(session_id: int) -> 'quiz_models.ScheduledSession | None':
    from asgiref.sync import sync_to_async
    from quiz.models import ScheduledSession
    from quiz.choices import SessionStatus

    def _inner():
        from celery.app.control import Control
        from src.celery_app import app as celery_app

        session = ScheduledSession.objects.filter(
            pk=session_id,
            status__in=[SessionStatus.PENDING, SessionStatus.RUNNING]
        ).first()
        if not session:
            return None

        control = Control(app=celery_app)
        for task_id in session.celery_task_ids:
            control.revoke(task_id, terminate=False)

        session.status = SessionStatus.CANCELLED
        session.save(update_fields=['status', 'updated_at'])
        return session

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

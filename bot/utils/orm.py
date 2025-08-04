from django.db import models
from django.utils import timezone
from django.utils.timezone import timedelta
from aiogram import types

from common import models as com_models
from quiz import models as quiz_models
from quiz.choices import QuizStatus
from support import models as support_models
from support.choices import SupportMessageStatus


async def get_users_count():
    return com_models.TelegramProfile.objects.aggregate(
        count=models.Count('id'),
    )['count']


async def get_support_messages_count():
    return support_models.SupportMessage.objects.aggregate(
        all=models.Count('id'),
        pending=models.Count('id', filter=models.Q(
            status=SupportMessageStatus.PENDING
        )),
        resolved=models.Count('id', filter=models.Q(
            status=SupportMessageStatus.RESOLVED
        )),
        rejected=models.Count('id', filter=models.Q(
            status=SupportMessageStatus.REJECTED
        ))
    )


async def get_data_solo():
    return com_models.Data.get_solo()


async def check_user_exists(chat: types.User):
    return com_models.TelegramProfile.objects.filter(chat_id=chat.id).exists()


async def get_user(chat: types.Chat | types.User, message=None, callback=None):
    user = com_models.TelegramProfile.objects.filter(chat_id=chat.id).first()
    if not user:
        user = com_models.TelegramProfile.objects.create(
            chat_id=chat.id,
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
        )
    return user


async def get_languages():
    return com_models.Language.objects.all()


async def get_categories():
    return quiz_models.Category.objects.all().values('id', 'title').order_by("order")


async def get_category_by_iterator(iterator: int):
    try:
        return tuple(quiz_models.Category.objects.all().order_by("order"))[:int(iterator)][-1]
    except Exception as e:
        return None

async def get_category_by_params(_id: int | str, title: str):
    return await quiz_models.Category.objects.filter(id=_id, title=title).values_list(
        'id', flat=True
    ).afirst()


async def create_pending_category(title: str):
    return quiz_models.Category.objects.create(title=title, status=False)


async def get_user_quizzes(user_id: int):
    return quiz_models.Quiz.objects.filter(owner_id=user_id).values('id', 'title').order_by('-created_at')


async def get_quizzes_by_category_id(category_id: str | int):
    return quiz_models.Quiz.objects.filter(
        category__id=category_id,
        privacy=False
    ).annotate(
        total_plays=models.Count('parts__user_quizzes')
    ).order_by('-quantity', '-total_plays').select_related("category", "owner")


async def get_quiz_by_id(quiz_id: int):
    return quiz_models.Quiz.objects.filter(id=quiz_id).select_related('owner', 'category').first()


async def get_quiz_values(quiz_id: int, values: list | tuple):
    return quiz_models.Quiz.objects.filter(id=quiz_id).values(*values).first()


async def get_quiz_parts(quiz_id: int):
    return quiz_models.QuizPart.objects.filter(quiz_id=quiz_id).select_related("quiz", "quiz__owner")


async def get_quiz_part(link: str):
    return await quiz_models.QuizPart.objects.filter(link=link).select_related("quiz", "quiz__owner").afirst()


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


async def create_support_message(owner_id: int, question: str):
    await support_models.SupportMessage.objects.acreate(
        owner_id=owner_id,
        question=question
    )


async def get_support_messages(owner_id: int):
    return support_models.SupportMessage.objects.filter(
        owner_id=owner_id,
        is_read=False,
        created_at__gte=timezone.now() - timedelta(days=7)
    )


async def get_support_message(message_id: int):
    return await support_models.SupportMessage.objects.filter(id=message_id).afirst()


async def get_pending_messages():
    return support_models.SupportMessage.objects.filter(
        status=SupportMessageStatus.PENDING
    )


# queries for group

async def exists_quiz_part(link: str):
    return quiz_models.QuizPart.objects.filter(link=link).exists()


async def get_group_quiz(group_id: str) -> quiz_models.GroupQuiz | None:
    group_quiz = await quiz_models.GroupQuiz.objects.filter(
        ~models.Q(status__in=[QuizStatus.FINISHED, QuizStatus.CANCELED]) & models.Q(group_id=group_id),
    ).prefetch_related(
        "part__questions", "part__questions__options"
    ).select_related('part', 'part__quiz', 'user').afirst()
    return group_quiz


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
        language: str,
):
    return await quiz_models.GroupQuiz.objects.acreate(
        part_id=part_id,
        user_id=user_id,
        group_id=group_id,
        message_id=message_id,
        title=title,
        invite_link=invite_link,
        language=language,
    )

async def add_or_check_chat(chat_id: int):
    data_obj = com_models.Data.get_solo()
    data_obj.channel_id = chat_id
    await data_obj.asave(update_fields=['channel_id'])


async def remove_chat(chat_id: int):
    data_obj = com_models.Data.get_solo()
    if data_obj.channel_id == chat_id:
        data_obj.channel_id = None
        await data_obj.asave(update_fields=['channel_id'])


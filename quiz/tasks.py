from celery import shared_task
from quiz.models import GroupQuiz

from bot.utils.methods import get_chat


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






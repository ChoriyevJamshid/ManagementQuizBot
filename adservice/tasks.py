import os
import logging
import time

from celery import shared_task
from django.utils.timezone import timedelta

from common.models import Data, TelegramProfile
from adservice.models import Media, Ad, Button


from src.settings import MEDIA_ROOT
from bot.utils import methods
from utils.functions import get_file_type


@shared_task
def get_file_id(media_id: int):
    data = Data.get_solo()

    obj = Media.objects.filter(id=media_id).first()
    if not obj:
        return

    extension = obj.file.name.split(".")[-1].lower()
    file_type = get_file_type(extension)
    file_path = str(os.path.join(MEDIA_ROOT, obj.file.name))

    for i in range(3):
        try:
            response = methods.send_file(
                chat_id=data.channel_id,
                file_path=file_path,
                file_type=file_type,
            )

            if response.status_code == 200:
                response_data = response.json()

                if file_type == 'photo':
                    photo = response_data.get('result', {}).get('photo', [])
                    file_id = None
                    if photo:
                        file_id = photo[0].get('file_id')
                else:
                    file_id = response_data.get('result', {}).get(f'{file_type}', {}).get('file_id')

                obj.file_id = file_id
                obj.file_type = file_type

                obj.save(update_fields=['file_id', 'file_type'])
                break
            else:
                time.sleep(2)
        except Exception as e:
            logging.error(f"Exception while getting file id: {e}")
            time.sleep(2)


@shared_task
def send_ad(ad_id: int):
    ad = Ad.objects.filter(pk=ad_id).prefetch_related("medias", "users").first()
    if not ad:
        return
    counter = 0

    if ad.language:
        users = TelegramProfile.objects.filter(language=ad.language)
    else:
        users = ad.users.all()

    if not users:
        users = TelegramProfile.objects.all()

    users_without_tests = users.exclude(user_quizzes__active=True).values_list('chat_id', flat=True).distinct()
    users_with_tests = users.filter(user_quizzes__active=True).values_list('id', flat=True).distinct()

    file_ids = ad.medias.filter(file_id__isnull=False).values('file_id', 'file_type')
    buttons = ad.buttons.all()

    reply_markup = None
    if buttons:
        reply_markup = dict()
        reply_markup['inline_keyboard'] = []
        for button in buttons:
            reply_markup['inline_keyboard'].append(
                [{
                    'text': button['text'],
                    'url': button['url'],
                }]
            )

    if users_with_tests:
        send_ad_after.delay(tuple(users_with_tests), ad.id)

    for user in users_without_tests:
        if file_ids:
            file_type = file_ids[0]['file_type']
            if len(file_ids) > 1:
                response = methods.send_multi_file_by_file_id(
                    chat_id=user,
                    file_type=file_type,
                    file_ids=[file['file_id'] for file in file_ids],
                    caption=ad.cleaned_content
                )
            else:
                response = methods.send_file(
                    chat_id=user,
                    file_type=file_type,
                    file_id=file_ids[0]['file_id'],
                    caption=ad.cleaned_content,
                    reply_markup=reply_markup
                )

        else:
            response = methods.send_text(
                chat_id=user,
                text=ad.cleaned_content,
                reply_markup=reply_markup,
            )
        if response.status_code == 200:
            counter += 1

    ad.is_sent = True
    ad.percent = f"{round(counter / len(users), 2) * 100} %"
    ad.save(update_fields=['is_sent', 'percent', 'updated_at'])


@shared_task
def send_ad_after(user_ids: list[int], ad_id: int):
    ad: Ad = Ad.objects.filter(id=ad_id).first()
    if not ad:
        return

    if ad.count >= 3:
        return

    title = f"{ad_id + 1} {ad.title}" if ad.title else None
    scheduled_at = ad.scheduled_at + timedelta(hours=1)

    new_ad = Ad.objects.create(
        title=title,
        content=ad.content,
        cleaned_content=ad.cleaned_content,
        scheduled_at=scheduled_at,
        count=ad.count + 1,
    )

    medias = ad.medias.all()
    if medias:
        new_ad.medias.set(medias)
    new_ad.users.set(user_ids)

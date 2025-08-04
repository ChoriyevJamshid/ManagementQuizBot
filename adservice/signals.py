import json

from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from django.utils.timezone import now, timedelta
from django_celery_beat.models import ClockedSchedule, PeriodicTask

from adservice.models import Media, Ad
from adservice.tasks import get_file_id

@receiver(post_save, sender=Media)
def save_media_file_id(sender, instance, created, **kwargs):
    if not instance.file_id:
        get_file_id.delay(instance.pk)


@receiver(post_save, sender=Ad)
def save_broadcast_task_id(sender, instance, created, **kwargs):


    if created:
        scheduled_at = instance.scheduled_at
        if scheduled_at < now():
            scheduled_at = now()

        clocked = ClockedSchedule.objects.create(
            clocked_time=scheduled_at + timedelta(seconds=15),
        )
        task = PeriodicTask.objects.create(
            name=f"Broadcast: #{instance.pk}, scheduled at {str(scheduled_at)}",
            task="adservice.tasks.send_ad",
            clocked=clocked,
            one_off=True,
            args=json.dumps([instance.id]),
        )
        instance.task_id = task.id
        instance.save(update_fields=['task_id'])
    else:
        task = PeriodicTask.objects.filter(id=instance.task_id).first()
        if not task:
            return

        scheduled_at = instance.scheduled_at
        if instance.scheduled_at != task.clocked.clocked_time - timedelta(seconds=15):
            if scheduled_at < now():
                scheduled_at = now()

            task.clocked.clocked_time = scheduled_at + timedelta(seconds=15)
            task.clocked.save(update_fields=['clocked_time'])


@receiver(post_delete, sender=Ad)
def delete_ad_task(sender, instance, **kwargs):
    if not instance.task_id:
        return

    task = PeriodicTask.objects.filter(id=instance.task_id).first()
    if not task:
        return

    task.delete()



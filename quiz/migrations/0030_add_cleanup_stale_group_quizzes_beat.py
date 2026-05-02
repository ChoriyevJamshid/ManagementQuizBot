from django.db import migrations


def add_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=15,
        period='minutes',
    )
    PeriodicTask.objects.update_or_create(
        name='cleanup_stale_group_quizzes',
        defaults={
            'task': 'quiz.tasks.cleanup_stale_group_quizzes',
            'interval': schedule,
            'enabled': True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='cleanup_stale_group_quizzes').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0029_replace_scheduledquiz_with_scheduledsession'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(add_periodic_task, remove_periodic_task),
    ]

from django.db import migrations


def add_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='18',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone='Asia/Tashkent',
    )
    PeriodicTask.objects.update_or_create(
        name='send_daily_group_stats',
        defaults={
            'task': 'quiz.tasks.send_daily_group_stats',
            'crontab': schedule,
            'enabled': True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='send_daily_group_stats').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0030_add_cleanup_stale_group_quizzes_beat'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(add_periodic_task, remove_periodic_task),
    ]

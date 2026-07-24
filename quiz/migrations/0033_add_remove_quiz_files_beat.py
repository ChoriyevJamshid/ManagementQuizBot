from django.db import migrations


def add_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period='days',
    )
    PeriodicTask.objects.update_or_create(
        name='remove_quiz_files',
        defaults={
            'task': 'quiz.tasks.remove_quiz_files',
            'interval': schedule,
            'enabled': True,
        },
    )

    # Leftover from the old ScheduledQuiz/run_scheduled_quiz system
    # (removed when ScheduledSession replaced it) — never cleaned up.
    PeriodicTask.objects.filter(name='scheduled_quiz_1').delete()


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='remove_quiz_files').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0032_add_weekly_group_stats_beat'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(add_periodic_task, remove_periodic_task),
    ]

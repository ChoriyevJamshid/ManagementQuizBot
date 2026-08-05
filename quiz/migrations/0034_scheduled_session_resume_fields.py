# Generated manually (no local Django env available) — mirrors the style of
# 0029_replace_scheduledquiz_with_scheduledsession.py. Verify with
# `python manage.py makemigrations --check` in an environment with Django installed
# before applying, to make sure it matches makemigrations' own output exactly.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0033_add_remove_quiz_files_beat'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledsession',
            name='current_part_index',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='scheduledsession',
            name='active_group_quiz_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='groupquiz',
            name='session_part_index',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='groupquiz',
            name='scheduled_session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='group_quizzes',
                to='quiz.scheduledsession',
            ),
        ),
    ]

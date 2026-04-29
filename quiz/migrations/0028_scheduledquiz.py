import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_celery_beat', '0018_improve_crontab_helptext'),
        ('quiz', '0027_alter_quiz_file_id_alter_quiz_title_and_more'),
        ('common', '0010_alter_data_file_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledQuiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group_id', models.CharField(max_length=63)),
                ('group_title', models.CharField(blank=True, max_length=255, null=True)),
                ('is_periodic', models.BooleanField(default=False)),
                ('hour', models.PositiveSmallIntegerField()),
                ('minute', models.PositiveSmallIntegerField()),
                ('days_of_week', models.CharField(default='*', max_length=31)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='scheduled_quizzes',
                    to='common.telegramprofile',
                )),
                ('quiz_part', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='scheduled_quizzes',
                    to='quiz.quizpart',
                )),
                ('periodic_task', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='scheduled_quiz',
                    to='django_celery_beat.periodictask',
                )),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

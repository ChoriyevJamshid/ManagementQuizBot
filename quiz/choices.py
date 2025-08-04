from django.db import models


class QuizStatus(models.TextChoices):
    INIT = "init", "init"
    STARTED = "started", "started"
    FINISHED = "finished", "finished"
    CANCELED = "canceled", "canceled"
    PAUSED = "paused", "paused"


class QuizPrivacy(models.TextChoices):
    PUBLIC = 'PUBLIC', 'PUBLIC'
    PRIVATE = 'PRIVATE', 'PRIVATE'



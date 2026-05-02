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


class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'



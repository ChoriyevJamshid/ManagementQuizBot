from django.db import models


class SupportMessageStatus(models.TextChoices):
    PENDING = 'pending', 'pending'
    RESOLVED = 'resolved', 'resolved'
    REJECTED = 'rejected', 'rejected'



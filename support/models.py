from django.db import models
from ckeditor.fields import RichTextField
from django.db.models import CharField

from support.choices import SupportMessageStatus
from utils.models import BaseModel


class SupportMessage(BaseModel):
    owner = models.ForeignKey("common.TelegramProfile", on_delete=models.CASCADE, related_name="support_messages")
    question = CharField(max_length=1024)
    answer = CharField(max_length=1024, blank=True, null=True)
    is_read = models.BooleanField(default=False)

    status = models.CharField(max_length=31, choices=SupportMessageStatus.choices, default=SupportMessageStatus.PENDING)

    objects = models.Manager()

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.question


import os
import orjson
from django.conf import settings
from django.db import models
from utils import BaseModel, Profile
from ckeditor.fields import RichTextField
from solo.models import SingletonModel


# Create your models here.


class TelegramProfile(Profile):
    is_registered = models.BooleanField(default=False)
    objects = models.Manager()

    class Meta:
        ordering = ('-created_at', 'role')

    def __str__(self):
        return self.username if self.username else self.first_name


class TelegramGroup(BaseModel):
    telegram_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    invite_link = models.CharField(max_length=512, blank=True, null=True)
    added_by = models.ForeignKey(
        'TelegramProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_groups',
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return f"{self.title} ({self.telegram_id})"


class Data(SingletonModel):
    file_types = models.JSONField(blank=True, null=True)
    video_urls = models.JSONField(blank=True, null=True)
    username = models.CharField(max_length=31, help_text="Bot username", blank=True, null=True)
    channel_id = models.BigIntegerField(default=0)

    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.video_urls:
            self.video_urls = {}
            if self.file_types:
                for file_type in self.file_types:
                    self.video_urls[file_type] = {}
                    self.video_urls[file_type]['url'] = ""

        if not self.file_types:
            self.file_types = []

        super().save(*args, **kwargs)

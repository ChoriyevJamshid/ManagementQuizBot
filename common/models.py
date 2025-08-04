import os
import orjson
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from utils import BaseModel, Profile, TextType
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

class Language(BaseModel):
    title = models.CharField(max_length=31)
    code = models.CharField(max_length=31, unique=True)

    objects = models.Manager()

    def __str__(self):
        return self.title

class TextCode(BaseModel):
    code = models.CharField(max_length=63, unique=True)

    objects = models.Manager()

    def __str__(self):
        return self.code

    class Meta:
        ordering = ('-created_at', 'code')


class Text(BaseModel):
    text = RichTextField()
    code = models.ForeignKey(TextCode, on_delete=models.CASCADE, related_name='texts')
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='texts')

    objects = models.Manager()

    def __str__(self):
        return self.text

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Data(SingletonModel):
    file_types = ArrayField(models.CharField(max_length=31), blank=True, null=True)
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

from django.db import models
from django.utils.timezone import now
from tinymce.models import HTMLField

from utils import BaseModel
from utils.functions import clean_from_html_for_tinymce

class Media(BaseModel):
    title = models.CharField(max_length=255, unique=True, null=True, blank=True)
    file = models.FileField(upload_to='medias/%Y/%m/%d')
    file_id = models.CharField(max_length=255, null=True, blank=True)
    file_type = models.CharField(max_length=15, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title if self.title else f"Media.id={self.pk}"


class Ad(BaseModel):
    title = models.CharField(max_length=255, unique=True, null=True, blank=True)
    content = HTMLField(blank=True, null=True, verbose_name="Контент", help_text="Не нужно, если выбран шаблон")
    cleaned_content = models.TextField(blank=True, null=True)

    medias = models.ManyToManyField(Media, blank=True, related_name="ads")
    users = models.ManyToManyField("common.TelegramProfile", blank=True, related_name="ads")
    language = models.CharField(max_length=7, blank=True, null=True)

    task_id = models.IntegerField(blank=True, null=True, editable=False)
    scheduled_at = models.DateTimeField(default=now, verbose_name="Расписание")
    percent = models.CharField(max_length=15, editable=False, verbose_name="Процент")
    is_sent = models.BooleanField(default=False, editable=False, verbose_name="Отправлено")

    count = models.PositiveSmallIntegerField(default=0, editable=False)

    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.scheduled_at:
            self.scheduled_at = now()

        if self.content:
            self.cleaned_content = clean_from_html_for_tinymce(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else f"Broadcast: #{self.id}"


class Button(BaseModel):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="buttons")
    text = models.CharField(max_length=31)
    url = models.URLField()
    order = models.PositiveSmallIntegerField(default=0)

    objects = models.Manager()

    class Meta:
        ordering = ('order',)

    def __str__(self):
        return self.text


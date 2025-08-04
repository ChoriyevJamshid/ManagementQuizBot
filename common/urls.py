from django.urls import path
from django.conf import settings

from .views import telegram_webhook

urlpatterns = [
    path(settings.WEBHOOK_PATH, telegram_webhook, name="telegram-webhook"),
]


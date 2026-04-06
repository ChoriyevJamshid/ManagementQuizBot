from import_export.admin import ImportExportModelAdmin
from solo.admin import SingletonModelAdmin
from django.contrib import admin

from .models import *
from .resources import (
    TelegramProfileResource
)


@admin.register(Data)
class DataAdmin(SingletonModelAdmin):
    pass


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ImportExportModelAdmin):
    list_display = ('id', 'chat_id', 'username', 'first_name', 'phone_number', 'role', 'created_at',)
    list_display_links = ('chat_id', 'username',)
    list_editable = ('role',)
    list_filter = ('role',)
    search_fields = ('chat_id', 'username', 'first_name', 'role')
    resource_class = TelegramProfileResource

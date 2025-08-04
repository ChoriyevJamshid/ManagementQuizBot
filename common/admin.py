from import_export.admin import ImportExportModelAdmin
from solo.admin import SingletonModelAdmin
from django.contrib import admin

from .models import *
from .resources import (
    TelegramProfileResource,
    LanguageResource,
    TextCodeResource,
    TextResource
)


class TextInline(admin.TabularInline):
    extra = 0
    model = Text


@admin.register(Data)
class DataAdmin(SingletonModelAdmin):
    pass


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ImportExportModelAdmin):
    list_display = ('id', 'chat_id', 'username', 'first_name', 'phone_number', 'language', 'role', 'created_at',)
    list_display_links = ('chat_id', 'username',)
    list_editable = ('role',)
    list_filter = ('role',)
    search_fields = ('chat_id', 'username', 'first_name', 'role')
    resource_class = TelegramProfileResource


@admin.register(Language)
class LanguageAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'code')
    list_display_links = 'title', 'code'
    resource_class = LanguageResource


@admin.register(TextCode)
class CodeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'code')
    list_display_links = ('code',)
    search_fields = ('code',)
    inlines = (TextInline,)
    resource_class = TextCodeResource


@admin.register(Text)
class TextAdmin(ImportExportModelAdmin):
    list_display = ('id', 'code', 'text', 'language',)
    list_display_links = ('id', 'code')
    list_editable = ('text', )
    search_fields = ('text',)
    resource_class = TextResource

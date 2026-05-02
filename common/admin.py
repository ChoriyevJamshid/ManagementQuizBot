from solo.admin import SingletonModelAdmin
from django.contrib import admin
from unfold.admin import ModelAdmin
from import_export.admin import ImportExportModelAdmin as BaseImportExportModelAdmin

from .models import Data, TelegramGroup, TelegramProfile
from .resources import TelegramProfileResource


@admin.register(TelegramGroup)
class TelegramGroupAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "telegram_id", "title", "username", "is_active", "added_by", "created_at")
    list_display_links = ("telegram_id", "title")
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = ("telegram_id", "title", "username")
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Group Info", {
            "classes": ("tab",),
            "fields": ("telegram_id", "title", "username", "invite_link", "is_active"),
        }),
        ("Meta", {
            "classes": ("tab",),
            "fields": ("added_by", "created_at", "updated_at"),
        }),
    )


@admin.register(Data)
class DataAdmin(ModelAdmin, SingletonModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    fieldsets = (
        ("Bot Settings", {
            "classes": ("tab",),
            "fields": ("username", "channel_id"),
        }),
        ("File Types & URLs", {
            "classes": ("tab",),
            "fields": ("file_types", "video_urls"),
        }),
    )


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ModelAdmin, BaseImportExportModelAdmin):
    resource_class = TelegramProfileResource
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "chat_id", "username", "first_name", "phone_number", "role", "is_registered", "created_at")
    list_display_links = ("chat_id", "username")
    list_editable = ("role",)
    list_filter = ("role", "is_registered")
    search_fields = ("chat_id", "username", "first_name", "phone_number")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Profile", {
            "classes": ("tab",),
            "fields": ("chat_id", "username", "first_name", "last_name", "phone_number", "role", "is_registered"),
        }),
        ("Dates", {
            "classes": ("tab",),
            "fields": ("created_at", "updated_at"),
        }),
    )

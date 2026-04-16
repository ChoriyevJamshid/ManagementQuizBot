from django.contrib import admin
from unfold.admin import ModelAdmin

from . import models


@admin.register(models.SupportMessage)
class SupportMessageAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "owner", "question", "status", "is_read", "created_at")
    list_display_links = ("id", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "is_read")
    search_fields = ("owner__username", "owner__first_name", "question")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("question", "owner", "created_at", "updated_at")

    fieldsets = (
        ("Message", {
            "classes": ("tab",),
            "fields": ("owner", "question", "status", "is_read"),
        }),
        ("Answer", {
            "classes": ("tab",),
            "fields": ("answer",),
        }),
        ("Dates", {
            "classes": ("tab",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner")

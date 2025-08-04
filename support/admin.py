from django.contrib import admin

from . import models


@admin.register(models.SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'question', 'answer', 'created_at', 'status',)
    list_display_links = ('id', 'created_at',)
    list_editable = ('status', 'answer')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner')



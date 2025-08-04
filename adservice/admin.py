from django.contrib import admin

from . import models


class TButtonInline(admin.TabularInline):
    model = models.Button
    extra = 0


@admin.register(models.Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_id', )


@admin.register(models.Ad)
class AdTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'percent', 'is_sent', 'created_at')
    list_filter = ('is_sent', )
    inlines = (TButtonInline,)



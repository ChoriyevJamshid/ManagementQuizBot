from django.contrib import admin
from django.apps import apps
from django.contrib import messages
from unfold.admin import ModelAdmin, TabularInline

from . import models
from utils.bot import set_my_commands


@admin.action(description="Set bot commands menu")
def set_bot_commands_menu(modeladmin, request, queryset):
    commands = list(queryset.values("command", "description").order_by("order"))
    response = set_my_commands(commands)
    if response.status_code == 200:
        modeladmin.message_user(request, "Bot commands set successfully", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Can't set bot commands", level=messages.ERROR)


class OptionInline(TabularInline):
    model = models.Option
    extra = 0
    show_change_link = True
    fields = ("text", "is_correct")


class QuestionInline(TabularInline):
    model = models.Question
    extra = 0
    show_change_link = True
    fields = ("text",)


class QuizPartInline(TabularInline):
    model = models.QuizPart
    extra = 0
    show_change_link = True
    fields = ("title", "link", "quantity", "from_i", "to_i")


class UserQuizInline(TabularInline):
    model = models.UserQuiz
    extra = 0
    show_change_link = True
    fields = ("user", "corrects", "wrongs", "skips", "status", "active")
    readonly_fields = ("corrects", "wrongs", "skips")


@admin.register(models.Category)
class CategoryAdmin(ModelAdmin):
    compressed_fields = True
    list_filter_submit = True

    list_display = ("id", "title", "order", "status")
    list_display_links = ("id", "title")
    list_editable = ("order", "status")
    list_filter = ("status",)
    search_fields = ("title",)
    ordering = ("-order",)
    list_per_page = 25


@admin.register(models.CategoryPending)
class CategoryPendingAdmin(ModelAdmin):
    compressed_fields = True
    list_filter_submit = True

    list_display = ("id", "title", "order", "status")
    list_display_links = ("id", "title")
    list_editable = ("order", "status")
    list_filter = ("status",)
    search_fields = ("title",)
    ordering = ("-order",)
    list_per_page = 25


@admin.register(models.Quiz)
class QuizAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "title", "timer", "privacy", "category", "quantity", "created_at")
    list_display_links = ("id", "title")
    list_editable = ("timer", "privacy")
    list_filter = ("privacy", "category")
    search_fields = ("title", "owner__username", "owner__first_name")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    inlines = (QuizPartInline,)

    fieldsets = (
        ("Quiz Info", {
            "tab": True,
            "fields": ("owner", "category", "title", "file_id", "quantity", "timer", "privacy"),
        }),
        ("Dates", {
            "tab": True,
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(models.QuizPart)
class QuizPartAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "link", "quiz", "quantity", "from_i", "to_i", "created_at")
    list_display_links = ("id", "link")
    search_fields = ("link", "quiz__title")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    inlines = (QuestionInline, UserQuizInline)

    fieldsets = (
        ("Part Info", {
            "tab": True,
            "fields": ("quiz", "title", "link", "quantity", "from_i", "to_i"),
        }),
        ("Dates", {
            "tab": True,
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("quiz")


@admin.register(models.Question)
class QuestionAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True

    list_display = ("id", "text", "part")
    list_display_links = ("id", "text")
    search_fields = ("text", "part__link")
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    inlines = (OptionInline,)

    fieldsets = (
        ("Question", {
            "tab": True,
            "fields": ("part", "text"),
        }),
        ("Dates", {
            "tab": True,
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("part")


@admin.register(models.UserQuiz)
class UserQuizAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = ("id", "part", "user", "corrects", "wrongs", "skips", "times", "status", "active", "created_at")
    list_display_links = ("id", "part")
    list_editable = ("status", "active")
    list_filter = ("status", "active")
    search_fields = ("user__first_name", "user__username", "part__link")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("corrects", "wrongs", "skips", "times", "created_at", "updated_at")

    fieldsets = (
        ("Session", {
            "tab": True,
            "fields": ("part", "user", "status", "active"),
        }),
        ("Results", {
            "tab": True,
            "fields": ("corrects", "wrongs", "skips", "times"),
        }),
        ("Dates", {
            "tab": True,
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "part")


@admin.register(models.GroupQuiz)
class GroupQuizAdmin(ModelAdmin):
    compressed_fields = True
    list_filter_submit = True

    list_display = (
        "id", "part", "user", "group_id", "title",
        "participant_count", "answers", "status", "created_at",
    )
    list_display_links = ("id", "part")
    list_filter = ("status",)
    search_fields = ("group_id", "title", "user__username", "user__first_name", "part__link")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = (
        "participant_count", "answers", "index", "skips",
        "poll_id", "message_id", "created_at", "updated_at",
    )

    fieldsets = (
        ("Session Info", {
            "tab": True,
            "fields": ("part", "user", "title", "group_id", "status", "invite_link"),
        }),
        ("Stats", {
            "tab": True,
            "fields": ("participant_count", "answers", "skips", "index", "is_answered"),
        }),
        ("Technical", {
            "tab": True,
            "fields": ("poll_id", "message_id", "file", "data"),
        }),
        ("Dates", {
            "tab": True,
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "part")


@admin.register(models.TelegramCommand)
class TelegramCommandAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True

    list_display = ("id", "command", "description", "order")
    list_display_links = ("id", "command")
    list_editable = ("order",)
    search_fields = ("command", "description")
    ordering = ("order",)
    actions = (set_bot_commands_menu,)


for model in apps.get_models():
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass

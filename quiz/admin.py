from django.contrib import admin
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
            "classes": ("tab",),
            "fields": ("owner", "category", "title", "file_id", "quantity", "timer", "privacy"),
        }),
        ("Dates", {
            "classes": ("tab",),
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
            "classes": ("tab",),
            "fields": ("quiz", "title", "link", "quantity", "from_i", "to_i"),
        }),
        ("Dates", {
            "classes": ("tab",),
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
            "classes": ("tab",),
            "fields": ("part", "text"),
        }),
        ("Dates", {
            "classes": ("tab",),
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
            "classes": ("tab",),
            "fields": ("part", "user", "status", "active"),
        }),
        ("Results", {
            "classes": ("tab",),
            "fields": ("corrects", "wrongs", "skips", "times"),
        }),
        ("Dates", {
            "classes": ("tab",),
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
            "classes": ("tab",),
            "fields": ("part", "user", "title", "group_id", "status", "invite_link"),
        }),
        ("Stats", {
            "classes": ("tab",),
            "fields": ("participant_count", "answers", "skips", "index", "is_answered"),
        }),
        ("Technical", {
            "classes": ("tab",),
            "fields": ("poll_id", "message_id", "file", "data"),
        }),
        ("Dates", {
            "classes": ("tab",),
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


@admin.action(description="Activate selected schedules")
def activate_schedules(modeladmin, request, queryset):
    queryset.update(is_active=True)
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(
        scheduled_quiz__in=queryset
    ).update(enabled=True)
    modeladmin.message_user(request, "Selected schedules activated.", level=messages.SUCCESS)


@admin.action(description="Deactivate selected schedules")
def deactivate_schedules(modeladmin, request, queryset):
    queryset.update(is_active=False)
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(
        scheduled_quiz__in=queryset
    ).update(enabled=False)
    modeladmin.message_user(request, "Selected schedules deactivated.", level=messages.SUCCESS)


@admin.register(models.ScheduledQuiz)
class ScheduledQuizAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    list_display = (
        "id", "quiz_part_display", "group_title", "group_id",
        "schedule_type_display", "time_display", "days_display",
        "created_by", "is_active", "created_at",
    )
    list_display_links = ("id", "quiz_part_display")
    list_editable = ("is_active",)
    list_filter = ("is_periodic", "is_active")
    search_fields = ("group_id", "group_title", "quiz_part__quiz__title", "created_by__username", "created_by__first_name")
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = ("periodic_task", "created_at", "updated_at")
    actions = (activate_schedules, deactivate_schedules)

    fieldsets = (
        ("Main", {
            "classes": ("tab",),
            "fields": ("created_by", "quiz_part", "group_id", "group_title", "is_active"),
        }),
        ("Schedule", {
            "classes": ("tab",),
            "fields": ("is_periodic", "hour", "minute", "days_of_week", "start_date"),
        }),
        ("Technical", {
            "classes": ("tab",),
            "fields": ("periodic_task",),
        }),
        ("Dates", {
            "classes": ("tab",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Quiz Part")
    def quiz_part_display(self, obj):
        return f"{obj.quiz_part.quiz.title} [{obj.quiz_part.from_i}–{obj.quiz_part.to_i}]"

    @admin.display(description="Type")
    def schedule_type_display(self, obj):
        return "🔄 Davriy" if obj.is_periodic else "📌 Bir martalik"

    @admin.display(description="Time")
    def time_display(self, obj):
        return f"{obj.hour:02d}:{obj.minute:02d}"

    @admin.display(description="Days")
    def days_display(self, obj):
        if not obj.is_periodic:
            return str(obj.start_date) if obj.start_date else "—"
        mapping = {
            '*': 'Har kuni',
            '1,2,3,4,5': 'Du–Ju',
            '0': 'Yakshanba', '1': 'Dushanba', '2': 'Seshanba',
            '3': 'Chorshanba', '4': 'Payshanba', '5': 'Juma', '6': 'Shanba',
        }
        return mapping.get(obj.days_of_week, obj.days_of_week)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "created_by", "quiz_part", "quiz_part__quiz", "periodic_task"
        )

from django.contrib import admin
from django.apps import apps
from django.contrib import messages

from . import models
from utils.bot import set_my_commands


@admin.action(description='Set bot commands menu')
def set_bot_commands_menu(modeladmin, request, queryset):
    commands = list(queryset.values("command", "description").order_by('order'))
    response = set_my_commands(commands)
    if response.status_code == 200:
        modeladmin.message_user(request, "Bot commands set successfully", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Can't set bot commands", level=messages.ERROR)


class OptionInline(admin.TabularInline):
    model = models.Option
    extra = 0


class QuestionInline(admin.TabularInline):
    model = models.Question
    extra = 0


class QuizPartInline(admin.TabularInline):
    model = models.QuizPart
    extra = 0


class UserQuizInline(admin.TabularInline):
    model = models.UserQuiz
    extra = 0


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'order', 'status')
    list_display_links = ('id', 'title')
    list_editable = ('order', 'status')
    ordering = ("-order",)


@admin.register(models.CategoryPending)
class CategoryPendingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'order', 'status')
    list_display_links = ('id', 'title')
    list_editable = ('order', 'status')
    ordering = ("-order",)


@admin.register(models.Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'timer', 'privacy')
    list_display_links = ('id', 'title')
    list_editable = ('timer', 'privacy')
    inlines = (QuizPartInline,)


@admin.register(models.QuizPart)
class QuizPartAdmin(admin.ModelAdmin):
    list_display = ('id', 'link', 'quantity', 'from_i', 'to_i')
    list_display_links = ('id', 'link')
    search_fields = ('link',)
    inlines = (QuestionInline, UserQuizInline,)


@admin.register(models.Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text')
    list_display_links = ('id', 'text')
    inlines = [OptionInline]


@admin.register(models.UserQuiz)
class UserQuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'part', 'user', 'corrects', 'wrongs', 'skips', 'times', 'status', 'active')
    list_display_links = ('id', 'part')
    list_editable = ('status', 'active')
    list_filter = ('status', 'active')
    search_fields = ('user__first_name', 'user__username', 'part')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'part')


@admin.register(models.GroupQuiz)
class GroupQuizAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'part', 'user', 'group_id',
        'participant_count', 'answers', 'invite_link', 'status'
    )
    list_display_links = ('id', 'part')
    list_filter = ('status', )


@admin.register(models.TelegramCommand)
class TelegramCommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'command', 'description')
    list_display_links = ('id', 'command')
    actions = (set_bot_commands_menu,)


for model in apps.get_models():
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass



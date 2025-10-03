from django.db import models
from utils.models import BaseModel
from .choices import QuizStatus
from . import managers


class Category(BaseModel):
    title = models.CharField(max_length=127, unique=True)
    order = models.PositiveIntegerField(default=1)
    status = models.BooleanField(default=True)

    objects = managers.CategoryManager()

    def __str__(self):
        return self.title


class CategoryPending(Category):
    objects = managers.CategoryPendingManager()

    class Meta:
        proxy = True


class Quiz(BaseModel):
    owner = models.ForeignKey(
        "common.TelegramProfile",
        on_delete=models.CASCADE,
        related_name="quizzes"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quizzes"
    )
    allowed_users = models.JSONField(
        default=list,
        blank=True,
        null=True
    )

    title = models.CharField(max_length=127)
    file_id = models.CharField(max_length=255)

    quantity = models.PositiveIntegerField()
    timer = models.PositiveSmallIntegerField()
    privacy = models.BooleanField(default=True)

    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.allowed_users:
            self.allowed_users = []
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class QuizPart(BaseModel):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="parts"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    link = models.CharField(
        max_length=31,
        unique=True
    )

    quantity = models.PositiveIntegerField(blank=True, null=True)
    from_i = models.PositiveIntegerField(blank=True, null=True)
    to_i = models.PositiveIntegerField(blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return self.link


class Question(BaseModel):
    part = models.ForeignKey(QuizPart, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()

    objects = models.Manager()


class Option(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    objects = models.Manager()


class UserQuiz(BaseModel):
    part = models.ForeignKey(
        QuizPart,
        on_delete=models.CASCADE,
        related_name="user_quizzes"
    )
    user = models.ForeignKey(
        "common.TelegramProfile",
        on_delete=models.CASCADE,
        related_name="user_quizzes"
    )

    corrects = models.IntegerField(default=0)
    wrongs = models.IntegerField(default=0)
    skips = models.IntegerField(default=0)
    times = models.BigIntegerField(default=0)

    data = models.JSONField(blank=True, null=True)
    current_data = models.JSONField(blank=True, null=True)

    status = models.CharField(max_length=31, choices=QuizStatus.choices, default=QuizStatus.STARTED)
    active = models.BooleanField(default=True)

    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.data:
            self.data = {}
        if not self.current_data:
            self.current_data = {}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UserQuiz -> {self.pk}"


class GroupQuiz(BaseModel):
    part = models.ForeignKey(
        QuizPart,
        on_delete=models.CASCADE,
        related_name="group_quizzes"
    )
    user = models.ForeignKey(
        "common.TelegramProfile",
        on_delete=models.CASCADE,
        related_name="group_quizzes"
    )

    title = models.CharField(
        max_length=127,
        blank=True,
        null=True
    )
    language = models.CharField(
        max_length=7,
        blank=True,
        null=True
    )
    invite_link = models.URLField(
        blank=True,
        null=True
    )
    group_id = models.CharField(max_length=63)
    message_id = models.CharField(max_length=255)
    poll_id = models.CharField(max_length=255)
    index = models.PositiveIntegerField(default=0)

    skips = models.PositiveSmallIntegerField(default=0)
    is_answered = models.BooleanField(default=False)
    answers = models.PositiveSmallIntegerField(default=0)
    participant_count = models.PositiveSmallIntegerField(default=0)

    file = models.FileField(
        upload_to="quiz/%Y/%m/%d",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=31,
        choices=QuizStatus.choices,
        default=QuizStatus.INIT
    )
    data = models.JSONField(
        blank=True,
        null=True
    )

    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.data:
            self.data = {}
        super().save()


class TelegramCommand(BaseModel):
    command = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=63)
    order = models.PositiveSmallIntegerField(default=1)
    objects = models.Manager()

    class Meta:
        ordering = ('order',)
        verbose_name = "Command"
        verbose_name_plural = 'Commands'

    def __str__(self):
        return self.command

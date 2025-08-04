from django.db import models

class Role(models.TextChoices):
    ADMIN = ('admin', 'admin')
    MODERATOR = ('moderator', 'moderator')
    USER = ('user', 'user')


class TextType(models.TextChoices):
    TEXT = 'text', 'text'
    BUTTON = 'button', 'button'
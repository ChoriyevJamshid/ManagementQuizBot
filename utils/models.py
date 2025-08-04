from django.db import models
from utils.choices import Role

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(BaseModel):

    chat_id = models.CharField(max_length=31, unique=True)
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=31, blank=True, null=True)
    role = models.CharField(max_length=255, choices=Role.choices, default=Role.USER)
    language = models.CharField(max_length=7,blank=True, null=True)

    class Meta:
        abstract = True

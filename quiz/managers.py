from django.db import models



class CategoryPendingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=False)


class CategoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=True)

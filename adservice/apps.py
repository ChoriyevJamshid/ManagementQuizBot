from django.apps import AppConfig


class AdserviceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adservice'

    def ready(self):
        import adservice.signals

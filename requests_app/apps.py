from django.apps import AppConfig


class RequestsAppConfig(AppConfig):
    name = 'requests_app'

class RequestsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'requests_app'

    def ready(self):
        import requests_app.signals

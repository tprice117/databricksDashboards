from django.apps import AppConfig


class DsIntercomConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communications"

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from .intercom.data_event import signals

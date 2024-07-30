from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        # This ensures that the signals within this app are imported and connected.
        from notifications import signals

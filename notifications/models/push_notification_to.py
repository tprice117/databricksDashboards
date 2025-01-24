from django.db import models
from django.utils import timezone
from django.conf import settings

from common.models import BaseModel


class PushNotificationTo(BaseModel):
    push_notification = models.ForeignKey(
        "notifications.PushNotification",
        on_delete=models.CASCADE,
        related_name="push_notification_tos",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    delivery_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    send_error = models.TextField(null=True, blank=True)

    def read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()

    def __str__(self):
        return self.user.full_name

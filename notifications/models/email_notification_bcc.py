from typing import List

from django.db import models

from api.models import BaseModel


class EmailNotificationBcc(BaseModel):
    email_notification = models.ForeignKey(
        "notifications.EmailNotification",
        on_delete=models.CASCADE,
        related_name="email_notification_bccs",
    )
    email = models.CharField(max_length=255)

    def __str__(self):
        return self.email

    def add_bcc(
        self,
    ):
        return None

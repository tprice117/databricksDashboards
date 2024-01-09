from typing import List

from django.db import models

from api.models import BaseModel


class EmailNotificationCc(BaseModel):
    email_notification = models.ForeignKey(
        "notifications.EmailNotification",
        on_delete=models.CASCADE,
        related_name="email_notification_ccs",
    )
    email = models.CharField(max_length=255)

    def __str__(self):
        return self.email

    def add_cc(
        self,
    ):
        return None

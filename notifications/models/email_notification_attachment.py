from django.db import models

from common.models import BaseModel


class EmailNotificationAttachment(BaseModel):
    email_notification = models.ForeignKey(
        "notifications.EmailNotification",
        on_delete=models.CASCADE,
        related_name="email_notification_attachments",
    )
    file_name = models.CharField(max_length=255)
    base64_data = models.TextField()

    def __str__(self):
        return self.email_notification.to_email

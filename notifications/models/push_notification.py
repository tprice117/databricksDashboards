from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder

from notifications.managers import PushNotificationManager
from common.models import BaseModel
from common.utils.get_file_path import get_file_path
from common.utils.customerio import send_push


def validate_image_file_size(img_file):
    filesize = img_file.size
    megabyte_limit = 1.0
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError(f"Max file size is {megabyte_limit} MB")


class PushNotification(BaseModel):
    template_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="The Customer IO template ID of the push notification.",
    )
    title = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="The title of the push notification.",
    )
    message = models.TextField(
        blank=True,
        null=True,
        help_text="The message to be displayed in the push notification.",
    )
    image = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        validators=[validate_image_file_size],
        help_text="The image to be displayed in the push notification. Max file size 1 MB.",
    )
    link = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="A deeplink or URL to redirect the user to.",
    )
    custom_data = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text="Custom data to be sent with the push notification. Only supports string key value pairs.",
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = PushNotificationManager()

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.id} - {self.title}"

    def read(self, user_id):
        """Mark the push notification as read for the user with the given user_id."""
        self.push_notification_tos.filter(user_id=user_id).update(
            is_read=True, read_at=timezone.now()
        )

    def send(self):
        """Send push notification to all users in the push_notification_tos field.
        Uses Customer IO API to send the push notification.
        """
        for push_to in self.push_notification_tos.all():
            success, ret_id = send_push(
                template_id=self.template_id,
                email=push_to.user.email,
                title=self.title,
                message=self.message,
                custom_data=self.custom_data,
                image_url=self.image.url if self.image else None,
                link=self.link,
            )
            if success:
                self.push_notification_tos.filter(id=push_to.id).update(
                    delivery_id=ret_id
                )
            else:
                self.push_notification_tos.filter(id=push_to.id).update(
                    send_error=ret_id
                )
        self.sent_at = timezone.now()
        self.save()

    @staticmethod
    def get_notifications_for_user(user):
        return PushNotification.objects.filter(push_notification_tos__user=user)

    @staticmethod
    def get_unread_notifications_for_user(user):
        return PushNotification.get_notifications_for_user(user).filter(is_read=False)

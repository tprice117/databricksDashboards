from django.conf import settings
import mailchimp_transactional as MailchimpTransactional
from django.db import models

from common.models import BaseModel
from notifications.models import (
    EmailNotificationAttachment,
    EmailNotificationBcc,
    EmailNotificationCc,
    EmailNotificationTo,
)


class EmailNotification(BaseModel):
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    from_email = models.CharField(max_length=255)
    reply_to = models.CharField(max_length=255)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return self.subject

    def send_email(self):
        """Send email using Mailchimp Transactional API with track_opens and track_clicks enabled.
        API Docs: https://mailchimp.com/developer/transactional/api/messages/send-new-message/
        """
        mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)
        to_addresses = self.add_tos() + self.add_ccs() + self.add_bccs()
        return mailchimp.messages.send(
            {
                "message": {
                    "from_name": "Downstream",
                    "from_email": self.from_email,
                    "to": to_addresses,
                    "subject": self.subject,
                    "track_opens": True,
                    "track_clicks": True,
                    "html": self.html_content,
                    "attachments": self.add_attachments(),
                }
            }
        )

    def add_tos(self: "EmailNotification"):
        emails = self.email_notification_tos.all()
        return [email.add_email() for email in emails]

    def add_ccs(self: "EmailNotification"):
        emails = self.email_notification_ccs.all()
        return [email.add_email() for email in emails]

    def add_bccs(self: "EmailNotification"):
        emails = self.email_notification_bccs.all()
        return [email.add_email() for email in emails]

    def add_attachments(self: "EmailNotification"):
        email_notification_attachments = self.email_notification_attachments.all()
        return [
            {
                # "type": "text/csv",
                "name": attachment.file_name,
                "content": attachment.base64_data,
            }
            for attachment in email_notification_attachments
        ]

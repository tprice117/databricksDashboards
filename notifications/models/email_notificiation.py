import mailchimp_transactional as MailchimpTransactional
from django.db import models

from api.models import BaseModel
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

    def __str__(self):
        return self.subject

    def send_email(self):
        mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")
        response = mailchimp.messages.send(
            {
                "message": {
                    "from_name": "Downstream",
                    "from_email": self.from_email,
                    "to": self.add_tos(),
                    "subject": self.subject,
                    "track_opens": True,
                    "track_clicks": True,
                    "html": self.html_content,
                    "attachments": self.add_attachments(),
                }
            }
        )

    def add_tos(self: "EmailNotification"):
        to_emails = self.email_notification_tos.all()
        return [to_email.add_to() for to_email in to_emails]

    def add_ccs(self: "EmailNotification"):
        cc_emails = self.email_notification_ccs.all()
        return []

    def add_bccs(self: "EmailNotification"):
        bcc_emails = self.email_notification_bccs.all()
        return []

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

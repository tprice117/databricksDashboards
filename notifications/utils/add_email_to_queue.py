import base64
from typing import List

from django.db import transaction

from notifications.models import (
    EmailNotification,
    EmailNotificationAttachment,
    EmailNotificationBcc,
    EmailNotificationCc,
    EmailNotificationTo,
)


class EmailAttachment:
    def __init__(self, file_name, base64_data):
        self.file_name = file_name
        self.base64_data = base64_data

    def decode_base64(self):
        """Decode Base64 data and return the binary content."""
        return base64.b64decode(self.base64_data)


def add_email_to_queue(
    from_email="noreply@trydownstream.io",
    to_emails: List[str] = [],
    subject=None,
    html_content=None,
    reply_to="noreply@trydownstream.io",
    cc_emails: List[str] = [],
    bcc_emails: List[str] = [],
    attachments: List[EmailAttachment] = [],
):
    """
    Method to create the database records for an email notification.
    Creates the EmailNotification instance, EmailNotificationTo instances,
    EmailNotificationCc instances, and EmailNotificationBcc instances.
    """

    with transaction.atomic():
        # Create EmailNotification instance.
        email_notification = EmailNotification.objects.create(
            from_email=from_email,
            subject=subject,
            html_content=html_content,
            reply_to=reply_to,
        )

        # Create EmailNotificationTo instances.
        for to_email in to_emails:
            EmailNotificationTo.objects.create(
                email_notification=email_notification, email=to_email
            )

        # Create EmailNotificationCc instances.
        for cc_email in cc_emails:
            EmailNotificationCc.objects.create(
                email_notification=email_notification, email=cc_email
            )

        # Create EmailNotificationBcc instances.
        for bcc_email in bcc_emails:
            EmailNotificationBcc.objects.create(
                email_notification=email_notification, email=bcc_email
            )

        # Create EmailNotificationAttachment instances.
        for attachment in attachments:
            EmailNotificationAttachment.objects.create(
                email_notification=email_notification,
                file_name=attachment.file_name,
                base64_data=attachment.base64_data,
            )


def add_internal_email_to_queue(
    from_email="noreply@trydownstream.io",
    subject=None,
    additional_to_emails: List[str] = [],
    html_content=None,
    reply_to="noreply@trydownstream.io",
    cc_emails: List[str] = [],
    bcc_emails: List[str] = [],
    attachments: List[EmailAttachment] = [],
):
    add_email_to_queue(
        from_email=from_email,
        to_emails=[
            "thayes@trydownstream.io",
            "zirwin@trydownstream.io",
            "jbaird@trydownstream.io",
        ]
        + additional_to_emails,
        subject=subject,
        html_content=html_content,
        reply_to=reply_to,
        cc_emails=cc_emails,
        bcc_emails=bcc_emails,
        attachments=attachments,
    )

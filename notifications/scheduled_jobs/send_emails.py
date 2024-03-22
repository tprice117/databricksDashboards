import datetime
import logging

from notifications.models import EmailNotification

logger = logging.getLogger(__name__)


def send_emails():
    emails_in_queue = EmailNotification.objects.filter(sent_at__isnull=True)

    for email in emails_in_queue:
        try:
            email.send_email()
            email.sent_at = datetime.datetime.now()
            email.save()
        except Exception as e:
            print("Email could not be sent. " + str(e))
            logger.error(f"scheduled_jobs.send_emails: [{e}]", exc_info=e)

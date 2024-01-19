import datetime

from notifications.models import EmailNotification


def send_emails():
    emails_in_queue = EmailNotification.objects.filter(sent_at__isnull=True)

    for email in emails_in_queue:
        try:
            email.send_email()
            email.sent_at = datetime.datetime.now()
            email.save()
        except:
            print("Email could not be sent.")

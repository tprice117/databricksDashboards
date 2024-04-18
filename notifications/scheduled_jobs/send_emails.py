import datetime
from django.utils import timezone
import pytz
import logging

from notifications.models import EmailNotification
from api.models import Order

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


def send_seller_order_emails():
    """Send emails to suppliers for pending orders.
    Run every 5 minutes, but only between 8am and 8pm (US/Central timezone).
    Send emails every 90 minutes.
    """
    orders = Order.objects.filter(status="PENDING")
    now_dt = timezone.now()
    now_dt_central = now_dt.astimezone(pytz.timezone("US/Central"))
    now_minus_hour = now_dt - datetime.timedelta(minutes=90)
    if 7 < now_dt_central.hour < 21:
        for order in orders:
            try:
                # Check if last email still hasn't been sent
                email_notification = (
                    EmailNotification.objects.filter(sent_at__isnull=True)
                    .filter(subject__icontains=order.id)
                    .first()
                )
                if not email_notification:
                    # Check last time this order email was sent
                    email_notification = (
                        EmailNotification.objects.exclude(sent_at__isnull=True)
                        .filter(sent_at__gt=now_minus_hour)
                        .filter(subject__icontains=order.id)
                        .first()
                    )
                if not email_notification:
                    order.send_supplier_approval_email()
            except Exception as e:
                print("send_seller_order_emails could not be sent. " + str(e))
                logger.error(
                    f"scheduled_jobs.send_seller_order_emails: [{e}]", exc_info=e
                )

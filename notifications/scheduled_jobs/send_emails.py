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
    Run every 5 minutes, but only between 6am and 11pm (US/Central timezone).
    Only send one email per order per hour max.
    """
    orders = Order.objects.filter(status="PENDING")
    now_dt = timezone.now()
    now_dt_central = now_dt.astimezone(pytz.timezone("US/Central"))
    now_minus_hour = now_dt - datetime.timedelta(hours=1)
    if 5 < now_dt_central.hour < 23:
        for order in orders:
            try:
                # Check last time this order email was sent
                email_notification = (
                    EmailNotification.objects.exclude(sent_at__isnull=True)
                    .filter(sent_at__gt=now_minus_hour)
                    .filter(subject__icontains=order.id)
                    .first()
                )
                if email_notification:
                    continue
                order.send_supplier_approval_email()
            except Exception as e:
                print("send_seller_order_emails could not be sent. " + str(e))
                logger.error(
                    f"scheduled_jobs.send_seller_order_emails: [{e}]", exc_info=e
                )

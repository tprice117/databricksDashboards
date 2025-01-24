import logging

from notifications.models import PushNotification

logger = logging.getLogger(__name__)


def send_push_notifications():
    push_in_queue = PushNotification.objects.filter(sent_at__isnull=True)

    for notification in push_in_queue:
        try:
            notification.send()
        except Exception as e:
            logger.error(f"scheduled_jobs.send_push_notifications: [{e}]", exc_info=e)

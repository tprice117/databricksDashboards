import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore

from api.scheduled_jobs.update_order_line_item_paid_status import (
    update_order_line_item_paid_status,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs 'paid' Stripe invoice line items with database."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Refresh OAuth Tokens. Run every 5 minutes.
        scheduler.add_job(
            update_order_line_item_paid_status,
            trigger=CronTrigger(minute="*/5"),
            id="update_order_line_item_paid_status",
            max_instances=1,
            replace_existing=False,
        )
        logger.info("Added job 'update_order_line_item_paid_status'.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore

from api.scheduled_jobs.create_stripe_invoices import create_stripe_invoices
from api.scheduled_jobs.update_order_line_item_paid_status import (
    update_order_line_item_paid_status,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs 'paid' Stripe invoice line items with database."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Sync OrderLineItem paid status from Stripe. Run every 5 minutes.
        scheduler.add_job(
            update_order_line_item_paid_status,
            trigger=CronTrigger(minute="*/5"),
            id="update_order_line_item_paid_status",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'update_order_line_item_paid_status'.")

        # Create Stripe invoices from last months orders. Run every day at 4am
        # on the 1st, 2nd, 3rd, 4th, and 5th of the month.
        scheduler.add_job(
            create_stripe_invoices,
            trigger=CronTrigger(day="1-5", hour="4"),
            id="create_stripe_invoices",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'create_stripe_invoices'.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

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
from api.scheduled_jobs.user_group_open_invoice_reminder import (
    user_group_open_invoice_reminder,
)
from api.utils.payouts import PayoutUtils
from notifications.scheduled_jobs.send_emails import send_emails

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs 'paid' Stripe invoice line items with database."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Sync OrderLineItem paid status from Stripe. Run every 5 minutes.
        scheduler.add_job(
            update_order_line_item_paid_status,
            trigger=CronTrigger(minute="*/1"),
            id="update_order_line_item_paid_status",
            max_instances=20,
            replace_existing=True,
        )
        logger.info("Added job 'update_order_line_item_paid_status'.")

        # Create Stripe invoices from last months orders. Run every day at 4am
        # on the 1st, 2nd, 3rd, 4th, and 5th of the month.
        # scheduler.add_job(
        #     create_stripe_invoices,
        #     trigger=CronTrigger(day="1-5", hour="*/4"),
        #     id="create_stripe_invoices",
        #     max_instances=1,
        #     replace_existing=True,
        # )
        # logger.info("Added job 'create_stripe_invoices'.")
        # scheduler.remove_job('create_stripe_invoices')

        # Send outstanding invoice reminder email. Run every 5 days.
        scheduler.add_job(
            user_group_open_invoice_reminder,
            trigger=CronTrigger(day="*/5"),
            id="user_group_open_invoice_reminder",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'user_group_open_invoice_reminder'.")

        # Send Emails. Run every 5 minutes.
        scheduler.add_job(
            send_emails,
            trigger=CronTrigger(minute="*/5"),
            id="send_emails",
            max_instances=20,
            replace_existing=True,
        )
        logger.info("Added job 'send_emails'.")

        # Send Payouts. Run every Wednesday, Thusday, and Friday at 6am.
        scheduler.add_job(
            PayoutUtils.send_payouts,
            trigger=CronTrigger(
                day_of_week="wed,thu,fri",
                hour="6",
                jitter=360,
            ),
            id="send_payouts",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'send_payouts'.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

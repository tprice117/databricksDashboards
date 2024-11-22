import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore

from api.scheduled_jobs.create_stripe_invoices import create_stripe_invoices
from api.scheduled_jobs.orders.create_auto_renewal_orders import (
    create_auto_renewal_orders,
)
from api.scheduled_jobs.update_order_line_item_paid_status import (
    update_order_line_item_paid_status,
)
from api.scheduled_jobs.user_group_open_invoice_reminder import (
    user_group_open_invoice_reminder,
)
from api.utils.payouts import PayoutUtils
from billing.scheduled_jobs.attempt_charge_for_past_due_invoices import (
    attempt_charge_for_past_due_invoices,
)
from billing.scheduled_jobs.ensure_invoice_settings_default_payment_method import (
    ensure_invoice_settings_default_payment_method,
)
from billing.scheduled_jobs.sync_invoices import sync_invoices
from billing.scheduled_jobs.consolidated_account_summary import (
    send_account_summary_emails,
)
from billing.scheduled_jobs.consolidated_account_past_due import (
    send_account_past_due_emails,
)
from billing.utils.billing import BillingUtils
from notifications.scheduled_jobs.send_emails import (
    send_emails,
    send_seller_order_emails,
)
from payment_methods.scheduled_jobs.sync_stripe_payment_methods import (
    sync_stripe_payment_methods,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs 'paid' Stripe invoice line items with database."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Sync OrderLineItem paid status from Stripe. Run every 10 minutes.
        scheduler.add_job(
            update_order_line_item_paid_status,
            trigger=CronTrigger(minute="*/10"),
            id="update_order_line_item_paid_status",
            max_instances=20,
            jitter=30,
            replace_existing=True,
        )

        # Send outstanding invoice reminder email. Run every 5 days.
        scheduler.add_job(
            user_group_open_invoice_reminder,
            trigger=CronTrigger(day="*/5"),
            id="user_group_open_invoice_reminder",
            max_instances=1,
            jitter=1260,
            replace_existing=True,
        )

        # Send Emails. Run every 5 minutes.
        scheduler.add_job(
            send_emails,
            trigger=CronTrigger(minute="*/5"),
            id="send_emails",
            max_instances=20,
            jitter=120,
            replace_existing=True,
        )

        # Sync Stripe Payment Methods. Run every 5 minutes.
        scheduler.add_job(
            sync_stripe_payment_methods,
            trigger=CronTrigger(minute="*/5"),
            id="sync_stripe_payment_methods",
            max_instances=2,
            jitter=30,
            replace_existing=True,
        )

        # Sync Stripe Payment Methods. Run every 5 minutes.
        scheduler.add_job(
            send_seller_order_emails,
            trigger=CronTrigger(minute="*/5"),
            id="send_seller_order_emails",
            max_instances=2,
            jitter=30,
            replace_existing=True,
        )

        # Sync Stripe Invoices. Run every 1 hour.
        scheduler.add_job(
            sync_invoices,
            trigger=CronTrigger(hour="*/1"),
            id="sync_invoices",
            max_instances=1,
            jitter=640,
            replace_existing=True,
        )

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

        # Send interval-based invoices. Run every day at 2am.
        scheduler.add_job(
            BillingUtils.run_interval_based_invoicing,
            trigger=CronTrigger(
                hour="2",
                jitter=640,
            ),
            id="run_interval_based_invoicing",
            max_instances=1,
            replace_existing=True,
        )

        # Send project-end based invoices. Run every day at 3am.
        scheduler.add_job(
            BillingUtils.run_project_end_based_invoicing,
            trigger=CronTrigger(
                hour="3",
                jitter=640,
            ),
            id="run_project_end_based_invoicing",
            max_instances=1,
            replace_existing=True,
        )

        # Attempt to charge a payment method on file for all past
        # due invoices. Run every day at 5am.
        scheduler.add_job(
            attempt_charge_for_past_due_invoices,
            trigger=CronTrigger(
                hour="5",
                jitter=640,
            ),
            id="attempt_charge_for_past_due_invoices",
            max_instances=1,
            replace_existing=True,
        )

        # Ensure that all Stripe Customer that have a Card on file
        # have a DefaultPaymentMethod set. Run every day at 1am.
        scheduler.add_job(
            ensure_invoice_settings_default_payment_method,
            trigger=CronTrigger(
                hour="1",
                jitter=640,
            ),
            id="ensure_invoice_settings_default_payment_method",
            max_instances=1,
            replace_existing=True,
        )

        # Create auto-renewal Orders for OrderGroups that need them.
        # Run every day at 3am.
        scheduler.add_job(
            create_auto_renewal_orders,
            trigger=CronTrigger(
                hour="3",
                jitter=640,
            ),
            id="create_auto_renewal_orders",
            max_instances=1,
            replace_existing=True,
        )

        # Send consolidated account summary emails. Run every Monday at 6am.
        scheduler.add_job(
            send_account_summary_emails,
            trigger=CronTrigger(
                day_of_week="mon",
                hour="6",
                jitter=360,
            ),
            id="send_account_summary_emails",
            max_instances=1,
            replace_existing=True,
        )

        # Send consolidated account summary emails. Run every Thursday at 6am.
        scheduler.add_job(
            send_account_past_due_emails,
            trigger=CronTrigger(
                day_of_week="thu",
                hour="6",
                jitter=360,
            ),
            id="send_account_past_due_emails",
            max_instances=1,
            replace_existing=True,
        )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

import datetime
import random
import time

import stripe
from django.conf import settings

from api.models import UserGroup
from api.utils.billing import BillingUtils
from common.utils.get_last_day_of_previous_month import get_last_day_of_previous_month

stripe.api_key = settings.STRIPE_SECRET_KEY


def send_stripe_invoices():
    user_groups = UserGroup.objects.all()

    # Loop through user groups to send invoices.
    for user_group in user_groups:
        # Based on invoice frequency, decide if we should send
        # invoices for this user group.
        if _should_send_invoice(user_group):
            try:
                BillingUtils.create_stripe_invoices_for_user_group(user_group)
            except Exception as e:
                print(f"Error sending invoices for user group {user_group.name}: {e}")
                pass


def _should_send_invoice(user_group):
    invoice_frequency = user_group.invoice_frequency
    is_friday = datetime.date.weekday() == 4
    is_first_day_of_month = datetime.date.day == 1

    if invoice_frequency == UserGroup.InvoiceFrequency.IMMEDIATELY:
        # Always send if IMMEDIATELY.
        return True
    elif invoice_frequency == UserGroup.InvoiceFrequency.WEEKLY and is_friday:
        # Only send on Fridays if WEEKLY.
        return True
    elif invoice_frequency == UserGroup.InvoiceFrequency.BI_WEEKLY and is_friday:
        # Only send on Fridays if BI_WEEKLY.
        return True
    elif (
        invoice_frequency == UserGroup.InvoiceFrequency.MONTHLY
        and is_first_day_of_month
    ):
        # Only send on the 1st of the month if MONTHLY.
        return True
    else:
        return False

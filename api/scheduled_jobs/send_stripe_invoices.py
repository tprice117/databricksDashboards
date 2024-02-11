import time

import stripe
from django.conf import settings

from api.models import Order
from common.utils.get_last_day_of_previous_month import get_last_day_of_previous_month

stripe.api_key = settings.STRIPE_SECRET_KEY


def send_stripe_invoices():
    # Get all Orders that have been completed and have an end date on
    # or before the last day of the previous month.
    orders = Order.objects.filter(
        status="COMPLETE",
        end_date__lte=get_last_day_of_previous_month(),
    )

    # Pause for 5 minutes.
    time.sleep(400)

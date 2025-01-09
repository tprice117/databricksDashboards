import datetime
from django.utils import timezone

from api.models import UserAddress, UserGroup
from common.utils.stripe.stripe_utils import StripeUtils
import logging

logger = logging.getLogger(__name__)


def attempt_charge_for_past_due_invoices():
    """
    Attempt to charge all past due invoices.
    """
    invoices = StripeUtils.Invoice.get_all()

    # Get the date 14 days ago.
    two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=14)

    # Filter for open invoices with a non zero amount due.
    all_open_invoices = list(
        filter(
            lambda invoice: invoice["status"] == "open"
            and invoice["amount_remaining"] > 0,
            invoices,
        )
    )
    # Filter for invoices that are due for the UserGroup/Account.
    invoices_due = []
    for invoice in all_open_invoices:
        # Get UserGroup for this invoice.
        user_address = UserAddress.objects.filter(
            stripe_customer_id=invoice["customer"],
        ).first()
        user_group = None
        if user_address:
            user_group = user_address.user_group
        else:
            invoices_due.append(invoice)
            logger.error(
                f"attempt_charge_for_past_due_invoices: stripe_customer_id: {invoice['customer']} not found for invoice {invoice['id']}"
            )
            continue
        # Check if invoice is due.
        if user_group and invoice["due_date"]:
            if user_group.net_terms == UserGroup.NetTerms.IMMEDIATELY:
                # due_date = (
                #     timezone.make_aware(
                #         timezone.datetime.fromtimestamp(invoice["due_date"]),
                #         timezone.get_current_timezone(),
                #     )
                #     if invoice["due_date"]
                #     else None
                # )
                # print(f"1 customer: {user_group.name} invoice due_date: {due_date}")
                invoices_due.append(invoice)
            elif invoice["due_date"] < two_weeks_ago.timestamp():
                # Give a 2 week grace period for net terms customers since we allow payment by check.
                # This allows for the check to be mailed and received by us before attempting to charge the card.
                invoices_due.append(invoice)
        else:
            # due_date = (
            #     timezone.make_aware(
            #         timezone.datetime.fromtimestamp(invoice["due_date"]),
            #         timezone.get_current_timezone(),
            #     )
            #     if invoice["due_date"]
            #     else None
            # )
            # if user_address and not user_group:
            #     print(f"2 customer: {user_address.name} invoice due_date: {due_date}")
            # If no due date (or no UserGroup), then we assume it is due immediately.
            invoices_due.append(invoice)

    # Attempt to charge invoices that are due.
    for past_due_invoice in invoices_due:
        # Attempt to pay the invoice. This function will attempt to pay with the default payment method.
        StripeUtils.Invoice.attempt_pay(past_due_invoice["id"])

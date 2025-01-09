import datetime

from api.models import UserGroup
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
        user_group_id = invoice["metadata"].get("user_group_id")
        # Check if invoice is due.
        if user_group_id and invoice["due_date"]:
            user_group = UserGroup.objects.filter(id=user_group_id).first()
            if not user_group:
                logger.error(
                    f"attempt_charge_for_past_due_invoices: UserGroup: {user_group_id} not found for invoice {invoice['id']}"
                )
                continue
            if user_group.net_terms == UserGroup.NetTerms.IMMEDIATELY:
                invoices_due.append(invoice)
            elif invoice["due_date"] < two_weeks_ago.timestamp():
                # Give a 2 week grace period for net terms customers since we allow payment by check.
                # This allows for the check to be mailed and received by us before attempting to charge the card.
                invoices_due.append(invoice)
        else:
            # If no due date (or no UserGroup), then we assume it is due immediately.
            invoices_due.append(invoice)

    # Attempt to charge invoices that are due.
    for past_due_invoice in invoices_due:
        # Attempt to pay the invoice. This function will attempt to pay with the default payment method.
        StripeUtils.Invoice.attempt_pay(past_due_invoice["id"])

import datetime

from common.utils.stripe.stripe_utils import StripeUtils


def attempt_charge_for_past_due_invoices():
    """
    Attempt to charge all past due invoices.
    """
    invoices = StripeUtils.Invoice.get_all()

    # Get the date 14 days ago.
    two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=14)

    # Filter for only past due invoices.
    past_due_invoices = list(
        filter(
            lambda invoice: invoice["status"] == "open"
            and invoice["amount_remaining"] > 0
            and (
                invoice["due_date"] is None
                or invoice["due_date"] < two_weeks_ago.timestamp()
            ),
            invoices,
        )
    )

    # Attempt to charge all past due invoices.
    for past_due_invoice in past_due_invoices:
        # Attempt to pay the invoice. This function will attempt to pay with the default payment method.
        StripeUtils.Invoice.attempt_pay(past_due_invoice["id"])

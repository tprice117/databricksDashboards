from django.db.models import Q
from django.utils import timezone

from api.models import UserGroup
from billing.models import Invoice
from payment_methods.models import PaymentMethod
from common.utils.stripe.stripe_utils import StripeUtils
import logging

logger = logging.getLogger(__name__)


def attempt_charge_for_past_due_invoices():
    """
    Attempt to charge all past due invoices in our db.
    """
    # Get all invoices that are not paid or void, and have a null due date
    # or a due date that is older than now and have a non-zero amount due.
    all_open_invoices = Invoice.objects.filter(
        ~Q(status=Invoice.Status.PAID)
        & ~Q(status=Invoice.Status.VOID)
        & ~Q(status=Invoice.Status.UNCOLLECTIBLE)
    ).filter(
        Q(due_date__isnull=True)
        | Q(due_date__lt=timezone.now()) & Q(amount_remaining__gt=0)
    )

    # Get the check buffer date (14 days ago).
    two_weeks_ago = timezone.now() - timezone.timedelta(days=14)

    # Filter for invoices that are due for the UserGroup/Account.
    invoices_due = []
    no_payment_method = []
    no_payment_method_credit_terms = []
    for invoice in all_open_invoices:
        # Get UserGroup for this invoice.
        user_address = invoice.user_address
        user_group = user_address.user_group
        # Check if invoice is due.
        if user_group and invoice.due_date:
            if user_group.net_terms == UserGroup.NetTerms.IMMEDIATELY:
                # print(
                #     f"1 customer: {user_group.name} invoice due_date: {invoice.due_date}"
                # )
                payment_methods = PaymentMethod.objects.filter(
                    user_group_id=user_group.id, active=True
                )
                if payment_methods.exists():
                    invoices_due.append(invoice)
                else:
                    no_payment_method.append(invoice)
            elif invoice.due_date < two_weeks_ago:
                # Give a 2 week grace period for net terms customers since we allow payment by check.
                # This allows for the check to be mailed and received by us before attempting to charge the card.
                payment_methods = PaymentMethod.objects.filter(
                    user_group_id=user_group.id, active=True
                )
                if payment_methods.exists():
                    invoices_due.append(invoice)
                else:
                    no_payment_method_credit_terms.append(invoice)
        else:
            # If no due date (or no UserGroup), then we assume it is due immediately.
            if invoice.user_address.user:
                payment_methods = PaymentMethod.objects.filter(
                    user_id=invoice.user_address.user.id
                )
                no_payment_method.append(invoice)
            invoices_due.append(invoice)

    # Attempt to charge invoices that are due.
    for past_due_invoice in invoices_due:
        # Attempt to pay the invoice. This function will attempt to pay with the default payment method.
        StripeUtils.Invoice.attempt_pay(past_due_invoice.invoice_id)

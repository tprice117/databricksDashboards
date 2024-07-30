import datetime

from api.models import UserAddress
from billing.models import Invoice
from common.utils.stripe.stripe_utils import StripeUtils


def sync_invoices():
    """
    Synchronizes database Invoice model with Stripe
    Invoices.
    """
    # Get all Stripe Invoices.
    stripe_invoices = StripeUtils.Invoice.get_all()

    # Update or create database Invoices.
    for stripe_invoice in stripe_invoices:
        user_address_exists = UserAddress.objects.filter(
            stripe_customer_id=stripe_invoice["customer"],
        ).exists()

        if user_address_exists:
            Invoice.objects.update_or_create(
                invoice_id=stripe_invoice["id"],
                defaults={
                    "user_address": UserAddress.objects.get(
                        stripe_customer_id=stripe_invoice["customer"],
                    ),
                    "amount_due": stripe_invoice["amount_due"] / 100,
                    "amount_paid": stripe_invoice["amount_paid"] / 100,
                    "amount_remaining": stripe_invoice["amount_remaining"] / 100,
                    "due_date": (
                        datetime.datetime.fromtimestamp(
                            stripe_invoice["due_date"],
                        )
                        if stripe_invoice["due_date"]
                        else None
                    ),
                    "hosted_invoice_url": stripe_invoice["hosted_invoice_url"],
                    "invoice_pdf": stripe_invoice["invoice_pdf"],
                    "metadata": stripe_invoice["metadata"],
                    "number": stripe_invoice["number"],
                    "paid": stripe_invoice["paid"],
                    "status": stripe_invoice["status"],
                    "total": stripe_invoice["total"] / 100,
                },
            )

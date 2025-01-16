from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from billing.typings import InvoiceResponse, InvoiceGroupedResponse
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils

if TYPE_CHECKING:
    from payment_methods.models.payment_method import PaymentMethod


def get_sorted_invoice_items(invoice_items):
    # Define the order of descriptions
    item_order = [
        "Service",
        "Rental",
        "Materials",
        "Fuel & Environmental Fee",
        "Delivery Fee",
        "Removal Fee",
    ]

    # Create a custom sorting function
    def get_sort_key(item):
        # Extract the main part of the description before the first space
        main_description = item["description"].split(" ")[0].strip()
        # Return the index of the main description in the item_order list
        index = (
            item_order.index(main_description)
            if main_description in item_order
            else len(item_order)
        )
        return index

    # Sort the items using the custom sorting function
    return sorted(invoice_items, key=get_sort_key)


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        OPEN = "open"
        PAID = "paid"
        VOID = "void"
        UNCOLLECTIBLE = "uncollectible"

    user_address = models.ForeignKey(
        "api.UserAddress",
        on_delete=models.CASCADE,
    )
    invoice_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe Invoice ID",
    )
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_remaining = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateTimeField(blank=True, null=True)
    hosted_invoice_url = models.URLField(blank=True, null=True)
    invoice_pdf = models.URLField(blank=True, null=True)
    metadata = models.JSONField()
    number = models.CharField(max_length=255, blank=True, null=True)
    paid = models.BooleanField()
    status = models.CharField(
        max_length=255,
        choices=Status.choices,
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    check_sent_at = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.invoice_id

    @lru_cache(maxsize=10)  # Do not recalculate this for the same object.
    def _get_invoice_items(self) -> InvoiceResponse:
        invoice = StripeUtils.Invoice.get(self.invoice_id)
        if invoice.lines["has_more"]:
            stripe_invoice_items = StripeUtils.InvoiceLineItem.get_all_for_invoice(
                self.invoice_id
            )
        else:
            stripe_invoice_items = invoice.lines["data"]
        groups = StripeUtils.SummaryItems.get_all_for_invoice(self.invoice_id)
        response: InvoiceResponse = {
            "items": [],
            "groups": [],
            "pre_payment_credit": 0,
            "post_payment_credit": 0,
        }

        if invoice["pre_payment_credit_notes_amount"]:
            response["pre_payment_credit"] = Decimal(
                invoice["pre_payment_credit_notes_amount"] / 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if invoice["post_payment_credit_notes_amount"]:
            response["post_payment_credit"] = Decimal(
                invoice["post_payment_credit_notes_amount"] / 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        for item in stripe_invoice_items:
            amount = Decimal(item["amount"] / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            tax = 0
            if item["tax_amounts"]:
                for tax_amount in item["tax_amounts"]:
                    tax += Decimal(tax_amount["amount"] / 100).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
            amount_excluding_tax = amount
            if item.get("amount_excluding_tax", None) is not None:
                amount_excluding_tax = Decimal(
                    item["amount_excluding_tax"] / 100
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            group_id = None
            if item.get("rendering", None) is not None:
                group_id = item["rendering"].get("summary_item", None)
            response["items"].append(
                {
                    "group_id": group_id,
                    "id": item["id"],
                    "amount": amount + tax,
                    "tax": tax,
                    "amount_excluding_tax": amount_excluding_tax,
                    "description": item["description"],
                    "order_line_item_id": item["metadata"].get("order_line_item_id"),
                }
            )
        for group in groups:
            response["groups"].append(
                {
                    "id": group["id"],
                    "description": group["description"],
                }
            )
        # setattr(self, "items", response["items"])
        # setattr(self, "groups", response["groups"])

        # Sort the items using the custom sorting function
        response["items"] = get_sorted_invoice_items(response["items"])

        return response

    @property
    def invoice_items(self) -> InvoiceResponse:
        return self._get_invoice_items()

    @property
    def invoice_items_grouped(self) -> InvoiceGroupedResponse:
        invoice_items = self._get_invoice_items()
        # Sort the items using the custom sorting function
        invoice_items["items"] = get_sorted_invoice_items(invoice_items["items"])

        for group in invoice_items["groups"]:
            group["total"] = 0
            group["items"] = []
            for item in invoice_items["items"]:
                if item["group_id"] == group["id"]:
                    group["items"].append(item)
                    group["total"] += item["amount"]
        ungrouped = {
            "id": "ungrouped",
            "description": "Ungrouped",
            "total": 0,
            "items": [],
        }
        for item in invoice_items["items"]:
            if item["group_id"] is None:
                ungrouped["items"].append(item)
                ungrouped["total"] += item["amount"]
        if ungrouped["items"]:
            invoice_items["groups"].append(ungrouped)
        return invoice_items

    def update_invoice(self, stripe_invoice=None):
        if stripe_invoice is None:
            invoice = StripeUtils.Invoice.get(self.invoice_id)
        else:
            invoice = stripe_invoice

        self.amount_due = invoice["amount_due"] / 100
        self.amount_paid = invoice["amount_paid"] / 100
        self.amount_remaining = invoice["amount_remaining"] / 100
        self.due_date = (
            timezone.datetime.fromtimestamp(
                invoice["due_date"],
            )
            if invoice["due_date"]
            else None
        )
        self.hosted_invoice_url = invoice["hosted_invoice_url"]
        self.invoice_pdf = invoice["invoice_pdf"]
        self.metadata = invoice["metadata"]
        self.number = invoice["number"]
        self.paid = invoice["paid"]
        self.status = invoice["status"]
        self.total = invoice["total"] / 100
        self.save()

    def pay_invoice(
        self,
        payment_method: "PaymentMethod",
    ):
        # Get Stripe Payment Method based on Payment Method.
        stripe_payment_method = payment_method.get_stripe_payment_method(
            user_address=self.user_address,
        )
        if stripe_payment_method is None:
            raise ValueError(
                "Payment method not found in Stripe. Please contact us for help."
            )

        # Pay the invoice.
        is_paid, invoice = StripeUtils.Invoice.attempt_pay_og(
            self.invoice_id,
            payment_method=stripe_payment_method.id,
            raise_error=True,
        )

        # Update the invoice.
        self.update_invoice(invoice)
        return is_paid

    @classmethod
    def update_or_create_from_invoice(cls, invoice, user_address):
        """Updates or creates an invoice from a Stripe invoice and UserAddress.

        Args:
            invoice (Dict): Stripe invoice object.
            user_address (Obj): UserAddress object.

        Returns:
            (obj, bool): The created or updated Invoice object and boolean denoting if it was created.
        """
        obj, created = cls.objects.update_or_create(
            invoice_id=invoice["id"],
            defaults={
                "user_address": user_address,
                "amount_due": invoice["amount_due"] / 100,
                "amount_paid": invoice["amount_paid"] / 100,
                "amount_remaining": invoice["amount_remaining"] / 100,
                "due_date": (
                    timezone.make_aware(
                        timezone.datetime.fromtimestamp(invoice["due_date"]),
                        timezone.get_current_timezone(),
                    )
                    if invoice["due_date"]
                    else None
                ),
                "hosted_invoice_url": invoice["hosted_invoice_url"],
                "invoice_pdf": invoice["invoice_pdf"],
                "metadata": invoice["metadata"],
                "number": invoice["number"],
                "paid": invoice["paid"],
                "status": invoice["status"],
                "total": invoice["total"] / 100,
            },
        )
        return obj, created

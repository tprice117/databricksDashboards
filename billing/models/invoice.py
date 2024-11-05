from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from django.db import models

from api.models.main_product.add_on import AddOn
from billing.typings import InvoiceResponse
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils
from payment_methods.models.payment_method import PaymentMethod


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

    def __str__(self):
        return self.invoice_id

    @lru_cache(maxsize=10)  # Do not recalculate this for the same object.
    def _get_invoice_items(self) -> InvoiceResponse:
        print("Getting invoice items")
        stripe_invoice_items = StripeUtils.InvoiceLineItem.get_all_for_invoice(
            invoice_id=self.invoice_id,
        )
        groups = StripeUtils.SummaryItems.get_all_for_invoice(self.invoice_id)
        response: InvoiceResponse = {
            "items": [],
            "groups": [],
        }
        for item in stripe_invoice_items:
            amount = Decimal(item["amount"] / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if item.get("amount_excluding_tax", None) is not None:
                amount_excluding_tax = Decimal(
                    item["amount_excluding_tax"] / 100
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            response["items"].append(
                {
                    "group_id": item["rendering"]["summary_item"],
                    "id": item["id"],
                    "amount": amount,
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
        return response

    @property
    def invoice_items(self) -> InvoiceResponse:
        return self._get_invoice_items()

    def pay_invoice(
        self,
        payment_method: PaymentMethod,
    ):
        # Get Stripe Payment Method.
        stripe_payment_method = payment_method.get_stripe_payment_method(
            user_address=self.user_address,
        )

        # Pay the invoice.
        StripeUtils.Invoice.attempt_pay_og(
            invoice_id=self.invoice_id,
            payment_method=stripe_payment_method.id,
        )

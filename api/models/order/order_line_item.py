from django.db import models

from api.models.order.order_line_item_type import OrderLineItemType
from common.models import BaseModel
from common.utils.stripe.stripe_utils import StripeUtils


class OrderLineItem(BaseModel):
    class PaymentStatus(models.TextChoices):
        NOT_INVOICED = "not_invoiced"
        INVOICED = "invoiced"
        PAID = "paid"

    order = models.ForeignKey(
        "api.Order", models.CASCADE, related_name="order_line_items"
    )
    order_line_item_type = models.ForeignKey(OrderLineItemType, models.PROTECT)
    rate = models.DecimalField(max_digits=18, decimal_places=2)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    platform_fee_percent = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=20,
        help_text="Enter as a percentage without the percent symbol (ex: 25.00)",
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    is_flat_rate = models.BooleanField(default=False)
    stripe_invoice_line_item_id = models.CharField(
        max_length=255, blank=True, null=True
    )
    paid = models.BooleanField(default=False)

    def __str__(self):
        return str(self.order) + " - " + self.order_line_item_type.name

    def get_invoice(self):
        if self.stripe_invoice_line_item_id:
            try:
                invoice_line_item = StripeUtils.InvoiceItem.get(
                    self.stripe_invoice_line_item_id
                )
                return StripeUtils.Invoice.get(invoice_line_item.invoice)
            except:
                # Return None if Stripe Invoice or Stripe Invoice Line Item does not exist.
                return None
        else:
            return None

    def payment_status(self):
        if not self.stripe_invoice_line_item_id:
            # Return None if OrderLineItem is not associated with an Invoice.
            return self.PaymentStatus.NOT_INVOICED
        elif self.stripe_invoice_line_item_id == "BYPASS":
            # Return True if OrderLineItem.StripeInvoiceLineItemId == "BYPASS".
            # BYPASS is used for OrderLineItems that are not associated with a
            # Stripe Invoice, but have been paid for by the customer.
            return self.PaymentStatus.PAID
        elif self.paid:
            # Return True if OrderLineItem.Paid == True. See below for how
            # OrderLineItem.Paid is set.
            return self.PaymentStatus.PAID
        else:
            # If OrderLineItem.StripeInvoiceLineItemId is populated and is not
            # "BYPASS" or OrderLineItem.Paid == False, the Order Line Item is
            # invoiced, but not paid.
            return self.PaymentStatus.INVOICED

    def seller_payout_price(self):
        return round((self.rate or 0) * (self.quantity or 0), 2)

    def customer_price(self):
        seller_price = self.seller_payout_price()
        customer_price = seller_price * (1 + (self.platform_fee_percent / 100))
        return round(customer_price, 2)

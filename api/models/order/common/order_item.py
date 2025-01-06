from django.db import models

from api.models import Order
from common.models import BaseModel


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        models.PROTECT,
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )
    customer_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="The rate the customer is charged for this item (ex: 25.00)",
    )
    seller_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="The rate the seller is paid for this item (ex: 20.00)",
    )
    # tax = models.DecimalField(
    #     max_digits=18,
    #     decimal_places=4,
    #     blank=True,
    #     null=True,
    # )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    stripe_invoice_line_item_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    paid = models.BooleanField(
        default=False,
    )

    class Meta:
        abstract = True

    def customer_price(self):
        """
        The customer price is the customer rate times the quantity.
        """
        return self.customer_rate * self.quantity

    def seller_price(self):
        """
        The seller price is the seller rate times the quantity.
        """
        return self.seller_rate * self.quantity

    def platform_fee(self):
        """
        The platform fee is the difference between the customer rate and the seller rate.
        This is the amount the platform takes from the transaction in dollars.
        """
        return self.customer_rate - self.seller_rate

    def platform_fee_percent(self):
        """
        The platform fee is the difference between the customer rate and the seller rate.
        This is the amount the platform takes from the transaction as a percentage.
        """
        return 100 * ((self.customer_price() / self.seller_price()) - 1)

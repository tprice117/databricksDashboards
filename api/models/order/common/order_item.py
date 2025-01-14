from django.db import models

from api.models.order.order_line_item_type import OrderLineItemType
from common.models import BaseModel


class OrderItem(BaseModel):
    order = models.ForeignKey(
        "api.Order",
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

    @property
    def customer_price(self):
        """
        The customer price is the customer rate times the quantity.
        """
        return (
            self.customer_rate * self.quantity
            if self.customer_rate and self.quantity
            else None
        )

    @property
    def seller_price(self):
        """
        The seller price is the seller rate times the quantity.
        """
        return (
            self.seller_rate * self.quantity
            if self.seller_rate and self.quantity
            else None
        )

    @property
    def platform_fee(self):
        """
        The platform fee is the difference between the customer rate and the seller rate.
        This is the amount the platform takes from the transaction in dollars.
        """
        return (
            self.customer_rate - self.seller_rate
            if self.customer_rate and self.seller_rate
            else None
        )

    @property
    def platform_fee_percent(self):
        """
        The platform fee is the difference between the customer rate and the seller rate.
        This is the amount the platform takes from the transaction as a percentage.
        """
        return (
            100 * ((self.customer_price / self.seller_price) - 1)
            if self.customer_price and self.seller_price
            else None
        )

    @property
    def stripe_tax_code_id(self):
        """
        Returns the tax rate for the specific order item.
        """
        # Try to get the order_line_item_type from the instance.
        # This is a "stop-gap" solution to set the order_line_item_type
        # directly on the OrderAdjustment instance.
        order_line_item_type = getattr(
            self,
            "order_line_item_type",
            None,
        )

        order_line_item_type_code = getattr(
            self,
            "order_line_item_type_code",
            None,
        )

        # If the order_line_item_type_code is set, try to get the OrderLineItemType.
        # If the OrderLineItemType exists, return the stripe_tax_code_id.
        # Otherwise, return the default tax code.
        if order_line_item_type:
            return order_line_item_type.stripe_tax_code_id
        elif order_line_item_type_code:
            order_line_item_type = OrderLineItemType.objects.filter(
                code=order_line_item_type_code,
            ).first()

            if order_line_item_type:
                return order_line_item_type.stripe_tax_code_id

        # If the order_line_item_type_code is not set or not found, return the
        # default tax code.
        return "txcd_20030000"

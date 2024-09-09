from typing import List

from django.db import models

from api.models.common.service import PricingService
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupService(PricingService):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="service",
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Deprecated. Use price_per_mile and flat_rate_price instead.",
    )
    miles = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Deprecated. Use price_per_mile and flat_rate_price instead.",
    )

    class Meta:
        verbose_name = "Booking Service (Legacy)"
        verbose_name_plural = "Booking Services (Legacy)"

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        self.rate = self.order_group.seller_product_seller_location.service.rate
        self.miles = self.order_group.seller_product_seller_location.service.miles
        self.save()

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupService. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for SERVICE.
        order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")

        return [
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=self.order_group.service.rate,
                quantity=self.order_group.service.miles or 1,
                is_flat_rate=self.order_group.service.miles is None,
                platform_fee_percent=self.order_group.take_rate,
            )
        ]

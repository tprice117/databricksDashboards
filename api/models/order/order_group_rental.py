from typing import List

from django.db import models

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
from common.models import BaseModel


class OrderGroupRental(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental",
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    price_per_day_additional = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        self.included_days = (
            self.order_group.seller_product_seller_location.rental.included_days
        )
        self.price_per_day_included = (
            self.order_group.seller_product_seller_location.rental.price_per_day_included
        )
        self.price_per_day_additional = (
            self.order_group.seller_product_seller_location.rental.price_per_day_additional
        )
        self.save()

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupRental. This method does not
        save the OrderLineItems to the database.
        """
        day_count = (order.end_date - order.start_date).days if order.end_date else 0
        days_over_included = day_count - self.order_group.rental.included_days

        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        order_line_items = []

        # Create OrderLineItem for Included Days.
        order_line_items.append(
            OrderLineItem(
                order=self,
                order_line_item_type=order_line_item_type,
                rate=self.order_group.rental.price_per_day_included,
                quantity=self.order_group.rental.included_days,
                description="Included Days",
                platform_fee_percent=self.order_group.take_rate,
            )
        )

        # Create OrderLineItem for Additional Days.
        if days_over_included > 0:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.order_group.rental.price_per_day_additional,
                    quantity=days_over_included,
                    description="Additional Days",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        return order_line_items

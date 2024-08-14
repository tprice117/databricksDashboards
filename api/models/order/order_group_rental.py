from typing import List

from django.db import models

from api.models.common.rental_two_step import PricingRentalTwoStep
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupRental(PricingRentalTwoStep):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental",
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
        Returns the OrderLineItems for this OrderGroupRental. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        line_items = self.get_price(duration=order.end_date - order.start_date)

        order_line_items: List[OrderLineItem] = []
        for line_item in line_items:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=line_item.unit_price,
                    quantity=line_item.quantity,
                    description=line_item.description,
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        return order_line_items

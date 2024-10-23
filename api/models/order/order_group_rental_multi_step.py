from typing import List

from django.db import models

from api.models.common.rental_multi_step import PricingRentalMultiStep
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupRentalMultiStep(PricingRentalMultiStep):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_multi_step",
    )

    class Meta:
        verbose_name = "Booking Rental Multi Step"
        verbose_name_plural = "Booking Rentals Multi Step"

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupRentalMultiStep. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        line_items = self.get_price(
            duration=order.end_date - order.start_date,
            shift_count=self.order_group.shift_count,
        )

        order_line_items: List[OrderLineItem] = []
        for line_item in line_items:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=line_item.unit_price,
                    quantity=line_item.quantity,
                    description=line_item.units.title(),
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        return order_line_items

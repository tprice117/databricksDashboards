import math
from typing import List

from django.db import models

from api.models.common.rental_one_step import PricingRentalOneStep
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupRentalOneStep(PricingRentalOneStep):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_one_step",
    )

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupMaterial. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        line_item = self.get_price(
            duration=order.end_date - order.start_date,
        )

        return [
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=line_item.unit_price,
                quantity=line_item.quantity,
                description=line_item.description,
                platform_fee_percent=self.order_group.take_rate,
            )
        ]

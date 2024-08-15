from typing import List

from django.db import models

from api.models.common.services_times_per_week import PricingServiceTimesPerWeek
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupServiceTimesPerWeek(PricingServiceTimesPerWeek):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="service_times_per_week",
    )

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupServiceTimesPerWeek. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for SERVICE.
        order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")

        line_item = self.get_price(
            times_per_week=self.order_group.times_per_week,
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

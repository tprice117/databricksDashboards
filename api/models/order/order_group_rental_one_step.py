import math
from typing import List

from django.db import models

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
from common.models import BaseModel


class OrderGroupRentalOneStep(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_one_step",
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupMaterial. This method does not
        save the OrderLineItems to the database.
        """
        days = (order.end_date - order.start_date).days

        # Get the number of 28-day periods, rounded up.
        periods = math.ceil(days / 28)

        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        return [
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=self.rate,
                quantity=periods,
                description="Rental",
                platform_fee_percent=self.order_group.take_rate,
            )
        ]

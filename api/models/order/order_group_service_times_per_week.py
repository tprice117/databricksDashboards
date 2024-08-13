from typing import List

from django.db import models

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
from common.models import BaseModel


class OrderGroupServiceTimesPerWeek(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="service_times_per_week",
    )
    one_time_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    two_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    three_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    four_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    five_times_per_week = models.DecimalField(
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
        Returns the OrderLineItems for this OrderGroupServiceTimesPerWeek. This method
        saves the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for SERVICE.
        order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")

        # Get the rate based on the number of times per week.
        rate = None

        if self.order_group.times_per_week == 1:
            rate = self.one_time_per_week
        elif self.order_group.times_per_week == 2:
            rate = self.two_times_per_week
        elif self.order_group.times_per_week == 3:
            rate = self.three_times_per_week
        elif self.order_group.times_per_week == 4:
            rate = self.four_times_per_week
        elif self.order_group.times_per_week == 5:
            rate = self.five_times_per_week
        else:
            rate = 0

        return [
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=rate,
                quantity=1,
                description=f"Service {self.order_group.times_per_week} times per week",
                platform_fee_percent=self.order_group.take_rate,
            )
        ]

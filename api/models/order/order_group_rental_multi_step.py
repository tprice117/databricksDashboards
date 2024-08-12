from typing import List

from django.db import models

from api.models.common.rental_multi_step import RentalMultiStep
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupRentalMultiStep(RentalMultiStep):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_multi_step",
    )

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupRentalMultiStep. This method does not
        save the OrderLineItems to the database.
        """
        # Get the OrderLineItemType for RENTAL.
        order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

        months, two_weeks, weeks, days, hours = self.get_most_efficient_pricing_pieces(
            duration=order.end_date - order.start_date
        )

        order_line_items = []

        # Create OrderLineItem for Months.
        if months:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.month,
                    quantity=months,
                    description="Rental (Monthly)",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        # Create OrderLineItem for Two Weeks.
        if two_weeks:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.two_weeks,
                    quantity=two_weeks,
                    description="Rental (Two Weeks)",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        # Create OrderLineItem for Weeks.
        if weeks:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.week,
                    quantity=weeks,
                    description="Rental (Weekly)",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        # Create OrderLineItem for Days.
        if days:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.day,
                    quantity=days,
                    description="Rental (Daily)",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        # Create OrderLineItem for Hours.
        if hours:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.hour,
                    quantity=hours,
                    description="Rental (Hourly)",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        return order_line_items

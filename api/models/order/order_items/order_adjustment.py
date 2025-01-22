from django.db import models

from api.models.order.common.order_item import OrderItem


class OrderAdjustment(OrderItem):
    # order_line_item_type = models.ForeignKey(
    #     "api.OrderLineItemType",
    #     on_delete=models.PROTECT,
    #     related_name="order_adjustments",
    # )

    class Meta:
        verbose_name = "Transaction Adjustment"
        verbose_name_plural = "Transaction Adjustments"

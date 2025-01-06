from api.models.order.common.order_item import OrderItem


class OrderAdjustment(OrderItem):
    pass

    class Meta:
        verbose_name = "Transaction Adjustment"
        verbose_name_plural = "Transaction Adjustments"

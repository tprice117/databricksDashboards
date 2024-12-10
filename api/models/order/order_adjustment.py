from api.models.order.common.order_item import OrderItem


class OrderAdjustment(OrderItem):
    pass

    class Meta:
        verbose_name = "Booking Adjustment"
        verbose_name_plural = "Booking Adjustments"

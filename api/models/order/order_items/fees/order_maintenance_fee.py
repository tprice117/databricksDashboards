from api.models.order.common.order_item import OrderItem


class OrderMaintenanceFee(OrderItem):
    order_line_item_type_code = "SERVICE"

    class Meta:
        verbose_name = "Transaction Maintenance Fee"
        verbose_name_plural = "Transaction Maintenance Fees"

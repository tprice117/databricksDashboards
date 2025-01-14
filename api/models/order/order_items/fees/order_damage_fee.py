from api.models.order.common.order_item import OrderItem


class OrderDamageFee(OrderItem):
    order_line_item_type_code = "DAMAGE"

    class Meta:
        verbose_name = "Transaction Damage Fee"
        verbose_name_plural = "Transaction Damage Fees"

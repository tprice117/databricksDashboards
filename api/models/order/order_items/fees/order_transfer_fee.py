from api.models.order.common.order_item import OrderItem


class OrderTransferFee(OrderItem):
    order_line_item_type_code = "DELIVERY"

    class Meta:
        verbose_name = "Transaction Transfer Fee"
        verbose_name_plural = "Transaction Transfer Fees"

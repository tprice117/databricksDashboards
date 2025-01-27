from api.models.order.common.order_item import OrderItem


class OrderMaterialFee(OrderItem):
    order_line_item_type_code = "MATERIAL"

    class Meta:
        verbose_name = "Transaction Material Fee"
        verbose_name_plural = "Transaction Material Fees"

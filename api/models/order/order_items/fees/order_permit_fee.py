from django.db import models

from api.models.order.common.order_item import OrderItem
from permits.models import Permit


class OrderPermitFee(OrderItem):
    order_line_item_type_code = "PERMIT"

    permit = models.ForeignKey(
        Permit,
        on_delete=models.PROTECT,
        related_name="order_permit_fees",
    )

    class Meta:
        verbose_name = "Transaction Permit Fee"
        verbose_name_plural = "Transaction Permit Fees"

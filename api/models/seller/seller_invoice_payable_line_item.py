from django.db import models

from api.models.order.order import Order
from api.models.seller.seller_invoice_payable import SellerInvoicePayable
from common.models import BaseModel


class SellerInvoicePayableLineItem(BaseModel):
    seller_invoice_payable = models.ForeignKey(
        SellerInvoicePayable, models.CASCADE, blank=True, null=True
    )
    order = models.ForeignKey(
        Order,
        models.CASCADE,
        related_name="seller_invoice_payable_line_items",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

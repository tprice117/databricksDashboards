from django.contrib import admin

from api.admin.inlines.seller_invoice_payable_line_item import (
    SellerInvoicePayableLineItemInline,
)
from api.models import SellerInvoicePayable


@admin.register(SellerInvoicePayable)
class SellerInvoicePayableAdmin(admin.ModelAdmin):
    model = SellerInvoicePayable
    list_display = ("seller_location", "supplier_invoice_id", "amount", "status")
    search_fields = ["id", "seller_location__name", "supplier_invoice_id"]
    inlines = [
        SellerInvoicePayableLineItemInline,
    ]

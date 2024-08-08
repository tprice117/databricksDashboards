from django.contrib import admin

from api.models import SellerInvoicePayableLineItem


@admin.register(SellerInvoicePayableLineItem)
class SellerInvoicePayableLineItemAdmin(admin.ModelAdmin):
    model = SellerInvoicePayableLineItem
    search_fields = ["id", "seller_invoice_payable__id", "order__id"]
    raw_id_fields = (
        "seller_invoice_payable",
        "order",
        "created_by",
        "updated_by",
    )

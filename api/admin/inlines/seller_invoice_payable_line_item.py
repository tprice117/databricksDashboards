from django.contrib import admin

from api.models import SellerInvoicePayableLineItem


class SellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0
    raw_id_fields = ("order",)

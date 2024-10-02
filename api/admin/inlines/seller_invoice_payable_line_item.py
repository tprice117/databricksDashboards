from django.contrib import admin

from api.models import SellerInvoicePayableLineItem, MainProduct


class SellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0
    raw_id_fields = ("order",)


class LinkedOrdersSIPLI(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0
    raw_id_fields = ("order",)
    verbose_name = "Linked Order"
    verbose_name_plural = "Linked Orders"


class InvoiceLineItem(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("backbill", "order")

    show_change_link = True
    extra = 0
    raw_id_fields = ("order",)
    verbose_name = "InvoiceLineItem"
    verbose_name_plural = "InvoiceLineItem"


# tables needed For Invoice Line Items:
# Product - mainProduct.name
# Service address - userAddress.name
# Type - rderlineitemtype.name
# Backbill - order.backbill
# Date -
# Rate -
# Quantity -
# Included -
# Amount - ""CalculatedField""
# total Amount - ""CalculatedField""

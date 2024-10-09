from django.contrib import admin

from api.models import SellerInvoicePayableLineItem, MainProduct, OrderLineItemType, OrderLineItem, Order


class SellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0
    raw_id_fields = ("order",)


class LinkedOrdersSellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("amount", "description")
    autocomplete_fields = [
        "order",
    ]
    inlines = [OrderLineItem]
    show_change_link = True
    extra = 0
    verbose_name = "Linked Order"
    verbose_name_plural = "Linked Orders"


# tables needed For Invoice Line Items:
# Product - mainProduct.name
# Service address - userAddress.name
# Type - orderlineitemtype.name
# Backbill - order.backbill
# Date - order.start_date
# Rate - orderlineitem.rate
# Quantity - orderlineitem.quantity
# Included - ?
# Amount - ""CalculatedField""
# total Amount - ""CalculatedField""

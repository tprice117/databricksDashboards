from django.contrib import admin

from api.models import (
    SellerInvoicePayableLineItem,
    MainProduct,
    OrderLineItemType,
    OrderLineItem,
    Order,
)
from api.models import *


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
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0
    verbose_name = "Linked Order"
    verbose_name_plural = "Linked Orders"

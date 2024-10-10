from django.contrib import admin

from api.models import SellerInvoicePayableLineItem, MainProduct, OrderLineItemType, OrderLineItem, Order
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

class SellerProductSellerLocationInline(admin.StackedInline):
    model = SellerProductSellerLocation
    extra = 0
class SellerProductInLine(admin.StackedInline):
    model = SellerProduct
    extra = 0
    fields = ['product', 'main_product']
class ProductInline(admin.StackedInline):
    model = Product
    extra = 0
    fields = ['name']  # Include fields you want to be editable    

# tables needed For Invoice Line Items:
# Product - mainProduct.name
# Service address - userAddress.name
# Type - orderlineitemtype.name
# Backbill - orderlineitem.backbill
# Date - order.start_date
# Rate - orderlineitem.rate
# Quantity - orderlineitem.quantity
# Included - ?
# Amount - ""CalculatedField""
# total Amount - ""CalculatedField""

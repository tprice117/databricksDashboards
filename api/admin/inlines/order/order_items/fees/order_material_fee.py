from api.admin.inlines.order.order_items.common.order_item_inline import OrderItemInline
from api.models import OrderMaterialFee
from common.admin.inlines.base_tabular_inline import BaseModelTabularInline


class OrderMaterialFeeInline(OrderItemInline):
    model = OrderMaterialFee
    show_change_link = True
    fields = [
        "quantity_decimal",
        "customer_rate_decimal",
        "seller_rate_decimal",
        "customer_price",
        "seller_price",
        "platform_fee",
        "platform_fee_percent",
        "description",
        "stripe_invoice_line_item_id",
        "paid",
    ] + BaseModelTabularInline.audit_fields
    readonly_fields = [
        "customer_price",
        "seller_price",
        "platform_fee",
        "platform_fee_percent",
        "stripe_invoice_line_item_id",
        "paid",
    ] + BaseModelTabularInline.readonly_fields
    extra = 0

from common.admin.inlines.base_tabular_inline import BaseModelTabularInline


class OrderItemInline(BaseModelTabularInline):
    show_change_link = True
    extra = 0
    fields = [
        "quantity",
        "customer_rate",
        "seller_rate",
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

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

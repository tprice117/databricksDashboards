from django import forms

from api.models.order.common.order_item import OrderItem
from common.admin.inlines.base_tabular_inline import BaseModelTabularInline


class OrderItemInlineForm(forms.ModelForm):
    pass

    class Meta:
        model = OrderItem
        fields = [
            "quantity",
            "customer_rate",
            "seller_rate",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_item: OrderItem = self.instance
        if order_item and order_item.stripe_invoice_line_item_id:
            # If the OrderItem has a Stripe Invoice Line Item ID, then make it read-only.
            for f in self.fields:
                self.fields[f].disabled = True


class OrderItemInline(BaseModelTabularInline):
    show_change_link = True
    extra = 0
    form = OrderItemInlineForm
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

    def customer_price(self, instance):
        """Override to format as currency with 2 decimal places."""
        return f"${instance.customer_price:.2f}" if instance.customer_price else None

    def seller_price(self, instance):
        """Override to format as currency with 2 decimal places."""
        return f"${instance.seller_price:.2f}" if instance.seller_price else None

    def platform_fee(self, instance):
        """Override to format as currency with 2 decimal places."""
        return f"${instance.platform_fee:.2f}" if instance.platform_fee else None

    def platform_fee_percent(self, instance):
        """Override to format as percentage with 2 decimal places."""
        return (
            f"{instance.platform_fee_percent:.2f}%"
            if instance.platform_fee_percent
            else None
        )

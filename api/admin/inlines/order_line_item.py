from django import forms
from django.contrib import admin

from api.models import OrderLineItem


class OrderLineItemInlineForm(forms.ModelForm):
    seller_payout_price = forms.CharField(required=False, disabled=True)
    customer_price = forms.CharField(required=False, disabled=True)
    is_paid = forms.BooleanField(required=False, disabled=True)

    class Meta:
        model = OrderLineItem
        fields = (
            "order_line_item_type",
            "description",
            "rate",
            "quantity",
            "seller_payout_price",
            "platform_fee_percent",
            "customer_price",
            "is_paid",
            "stripe_invoice_line_item_id",
            "backbill",
        )
        readonly_fields = (
            "seller_payout_price",
            "customer_price",
            "is_paid",
            "stripe_invoice_line_item_id",
        )
        raw_id_fields = ("order_line_item_type",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_line_item: OrderLineItem = self.instance
        if order_line_item and order_line_item.stripe_invoice_line_item_id:
            # If the OrderLineItem has a Stripe Invoice Line Item ID, then make it read-only.
            for f in self.fields:
                self.fields[f].disabled = True

        # Set initial values for read-only fields.
        self.initial["seller_payout_price"] = order_line_item.seller_payout_price()
        self.initial["customer_price"] = order_line_item.customer_price()
        self.initial["is_paid"] = (
            order_line_item.payment_status() == OrderLineItem.PaymentStatus.PAID
        )


class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    form = OrderLineItemInlineForm
    show_change_link = True
    extra = 0

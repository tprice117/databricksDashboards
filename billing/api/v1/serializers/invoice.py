from decimal import Decimal
from rest_framework import serializers

from api.serializers import UserAddressSerializer
from billing.models import Invoice
from billing.typings import InvoiceItem, InvoiceGroup
from payment_methods.models import PaymentMethod


class InvoiceSerializer(serializers.ModelSerializer):
    user_address = UserAddressSerializer()

    class Meta:
        model = Invoice
        fields = "__all__"


class InvoiceItemSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    id = serializers.CharField()
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_excluding_tax = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_line_item_id = serializers.CharField()


class InvoiceGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    description = serializers.CharField()


class InvoiceExpandedSerializer(serializers.ModelSerializer):
    user_address = UserAddressSerializer()
    items = serializers.SerializerMethodField(read_only=True)
    groups = serializers.SerializerMethodField(read_only=True)
    pre_payment_credit = serializers.SerializerMethodField(read_only=True)
    post_payment_credit = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"

    def get_items(self, obj) -> InvoiceItem:
        return obj.invoice_items["items"]

    def get_groups(self, obj) -> InvoiceGroup:
        return obj.invoice_items["groups"]

    def get_pre_payment_credit(self, obj) -> Decimal:
        return obj.invoice_items["pre_payment_credit"]

    def get_post_payment_credit(self, obj) -> Decimal:
        return obj.invoice_items["post_payment_credit"]


class PayInvoiceRequestSerializer(serializers.Serializer):
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.all(),
        write_only=True,
    )


class PayInvoiceResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    # invoice = InvoiceExpandedSerializer()

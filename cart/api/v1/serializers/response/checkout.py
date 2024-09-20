from rest_framework import serializers

from cart.models import CheckoutOrder
from api.serializers import OrderSerializer


class CheckoutResponseSerializer(serializers.ModelSerializer):
    orders = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = CheckoutOrder
        fields = (
            "id",
            "user_address",
            "orders",
            "payment_method",
            "pay_later",
            "customer_price",
            "seller_price",
            "estimated_taxes",
            "code",
        )

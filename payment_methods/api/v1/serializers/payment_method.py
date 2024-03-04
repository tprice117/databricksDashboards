from rest_framework import serializers

from payment_methods.api.v1.serializers.payment_method_user import (
    PaymentMethodUserSerializer,
)
from payment_methods.api.v1.serializers.payment_method_user_address import (
    PaymentMethodUserAddressSerializer,
)
from payment_methods.models import PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    card = serializers.SerializerMethodField(read_only=True)
    payment_method_user_addresses = PaymentMethodUserAddressSerializer(
        many=True, read_only=True
    )
    payment_method_users = PaymentMethodUserSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentMethod
        fields = (
            "id",
            "token",
            "user",
            "user_group",
            "card",
            "payment_method_user_addresses",
            "payment_method_users",
        )

    def get_card(self, instance):
        return {
            "number": instance.card_number,
            "brand": instance.card_brand,
            "expiration_month": instance.card_exp_month,
            "expiration_year": instance.card_exp_year,
        }

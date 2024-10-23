from rest_framework import serializers
from typing import TypedDict, Union

from payment_methods.api.v1.serializers.payment_method_user import (
    PaymentMethodUserSerializer,
)
from payment_methods.api.v1.serializers.payment_method_user_address import (
    PaymentMethodUserAddressSerializer,
)
from payment_methods.models import PaymentMethod


class CreditCardType(TypedDict):
    # https://developers.basistheory.com/docs/api/tokens/#card-object
    number: Union[str, None]
    brand: Union[str, None]
    # Two-digit number representing the card's expiration month
    expiration_month: Union[int, None]
    # Four-digit number representing the card's expiration year
    expiration_year: Union[int, None]


class PaymentMethodSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    card = serializers.SerializerMethodField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    reason = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = (
            "id",
            "token",
            "user",
            "user_group",
            "card",
            "active",
            "reason",
        )

    def get_card(self, instance) -> CreditCardType:
        return instance.get_card()

    def get_reason(self, instance) -> str:
        return instance.inactive_reason

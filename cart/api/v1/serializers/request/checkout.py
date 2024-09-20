from rest_framework import serializers

from api.models import UserAddress
from payment_methods.models import PaymentMethod


class CheckoutRequestSerializer(serializers.Serializer):
    user_address = serializers.PrimaryKeyRelatedField(
        queryset=UserAddress.objects.all(),
        write_only=True,
        allow_null=False,
    )
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

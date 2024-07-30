from rest_framework import serializers

from payment_methods.models.payment_method_user_address import PaymentMethodUserAddress


class PaymentMethodUserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    default = serializers.BooleanField(
        read_only=True,
        source="is_default_payment_method",
        help_text="Indicates if this PaymentMethod is the default for the UserAddress.",
    )

    class Meta:
        model = PaymentMethodUserAddress
        fields = "__all__"

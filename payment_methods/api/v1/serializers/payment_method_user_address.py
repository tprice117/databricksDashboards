from rest_framework import serializers

from payment_methods.models.payment_method_user_address import PaymentMethodUserAddress


class PaymentMethodUserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = PaymentMethodUserAddress
        fields = "__all__"

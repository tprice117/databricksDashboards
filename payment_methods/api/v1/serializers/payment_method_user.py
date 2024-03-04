from rest_framework import serializers

from payment_methods.models.payment_method_user import PaymentMethodUser


class PaymentMethodUserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = PaymentMethodUser
        fields = "__all__"

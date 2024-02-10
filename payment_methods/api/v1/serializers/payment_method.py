from rest_framework import serializers

from payment_methods.models import PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    card = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = (
            "id",
            "token",
            "user",
            "user_group",
            "card",
        )

    def get_card(self, instance):
        return {
            "number": instance.card_number,
            "brand": instance.card_brand,
            "expiration_month": instance.card_exp_month,
            "expiration_year": instance.card_exp_year,
        }

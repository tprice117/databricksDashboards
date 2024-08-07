from rest_framework import serializers

from pricing_engine.models import PricingLineItem


class PricingLineItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.FloatField()

    class Meta:
        model = PricingLineItem
        fields = [
            "description",
            "quantity",
            "unit_price",
            "units",
            "total",
        ]

from rest_framework import serializers

from pricing_engine.models import PricingLineItemGroup


class PricingLineItemGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingLineItemGroup
        fields = [
            "title",
            "total",
        ]

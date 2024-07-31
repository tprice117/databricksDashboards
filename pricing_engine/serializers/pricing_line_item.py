from rest_framework import serializers

from pricing_engine.models import PricingLineItem


class PricingLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingLineItem

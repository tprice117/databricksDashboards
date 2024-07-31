from rest_framework import serializers

from pricing_engine.models import PricingLineItemGroup


class PricingLineItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingLineItemGroup

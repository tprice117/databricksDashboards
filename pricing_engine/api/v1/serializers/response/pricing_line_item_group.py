from typing import Tuple

from rest_framework import serializers

from pricing_engine.api.v1.serializers.response.pricing_line_item import (
    PricingLineItemSerializer,
)
from pricing_engine.models import PricingLineItemGroup
from pricing_engine.models.pricing_line_item import PricingLineItem


class PricingLineItemGroupSerializer(serializers.ModelSerializer):
    items = PricingLineItemSerializer(many=True)

    class Meta:
        model = PricingLineItemGroup
        fields = [
            "title",
            "items",
            "total",
        ]

    def to_representation(
        self, instance: Tuple[PricingLineItemGroup, list[PricingLineItem]]
    ):
        response_data = {}
        response_data["title"] = instance[0].title
        response_data["items"] = PricingLineItemSerializer(instance[1], many=True).data
        response_data["total"] = self.get_total(instance[1])
        return response_data

    def get_total(self, instance: list[PricingLineItem]):
        return sum([item.total for item in instance])

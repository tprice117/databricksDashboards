from typing import List, Tuple

from rest_framework import serializers

from pricing_engine.api.v1.serializers.response.pricing_line_item_group import (
    PricingLineItemGroupSerializer,
)
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class PricingEngineResponseSerializer(serializers.Serializer):
    service = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    rental = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    material = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    delivery = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    removal = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    fuel_and_environmental = PricingLineItemGroupSerializer(
        read_only=True,
        allow_null=True,
    )
    total = serializers.DecimalField(
        read_only=True,
        max_digits=10,
        decimal_places=2,
    )

    def to_representation(
        self,
        instance: List[Tuple[PricingLineItemGroup, List[PricingLineItem]]],
    ):
        # Default all values to None.
        response = {
            "service": None,
            "rental": None,
            "material": None,
            "delivery": None,
            "removal": None,
            "fuel_and_environmental": None,
        }

        # Loop through the instance and create a dictionary with the keys.
        group_and_items: Tuple[PricingLineItemGroup, list[PricingLineItem]]
        for group_and_items in instance:
            if group_and_items[0].code == "service":
                response["service"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data
            elif group_and_items[0].code == "rental":
                response["rental"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data
            elif group_and_items[0].code == "material":
                response["material"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data
            elif group_and_items[0].code == "delivery":
                response["delivery"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data
            elif group_and_items[0].code == "removal":
                response["removal"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data
            elif group_and_items[0].code == "fuel_and_environmental":
                response["fuel_and_environmental"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data

        response["total"] = self.get_total(instance)

        return response

    def get_total(self, instance: list[(PricingLineItemGroup, list[PricingLineItem])]):
        return sum(
            [sum([x.total for x in group_and_items[1]]) for group_and_items in instance]
        )

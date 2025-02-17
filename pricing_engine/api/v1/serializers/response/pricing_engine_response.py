from typing import List, Tuple

from rest_framework import serializers

from pricing_engine.api.v1.serializers.response.pricing_line_item_group import (
    PricingLineItemGroupSerializer,
)
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class RentalBreakdownPartSerializer(serializers.Serializer):
    base = serializers.FloatField()
    rpp_fee = serializers.FloatField(allow_null=True)
    fuel_fees = serializers.FloatField()
    estimated_taxes = serializers.FloatField(allow_null=True)
    subtotal = serializers.FloatField()
    total = serializers.FloatField()


class RentalBreakdownSerializer(serializers.Serializer):
    day = RentalBreakdownPartSerializer(allow_null=True)
    week = RentalBreakdownPartSerializer(allow_null=True)
    month = RentalBreakdownPartSerializer(allow_null=True)


class PriceBreakdownPart(serializers.Serializer):
    fuel_and_environmental = serializers.FloatField()
    tax = serializers.FloatField()
    total = serializers.FloatField()


class PriceBreakdown(serializers.Serializer):
    other = PriceBreakdownPart()
    one_time = PriceBreakdownPart()
    rental = RentalBreakdownSerializer()


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
    tax = serializers.DecimalField(
        read_only=True,
        max_digits=10,
        decimal_places=2,
    )
    breakdown = PriceBreakdown(read_only=True, allow_null=True)

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
            elif (
                group_and_items[0].code == "fuel_and_environmental"
                or group_and_items[0].code == "fuel_and_env"
            ):
                response["fuel_and_environmental"] = PricingLineItemGroupSerializer(
                    group_and_items
                ).data

        response["total"] = self.get_total(instance)
        response["tax"] = self.get_tax(instance)

        return response

    def get_total(self, instance: list[(PricingLineItemGroup, list[PricingLineItem])]):
        return sum(
            [sum([x.total for x in group_and_items[1]]) for group_and_items in instance]
        )

    def get_tax(self, instance: list[(PricingLineItemGroup, list[PricingLineItem])]):
        all_taxes = []
        for group_and_items in instance:
            all_taxes.extend([x.tax for x in group_and_items[1] if x.tax is not None])
        return float(sum(all_taxes)) if all_taxes else 0

from rest_framework import serializers

from pricing_engine.api.v1.serializers.request.pricing_engine_request import (
    PricingEngineRequestSerializer,
)


class PricingEngineRequestByLatLongSerializer(PricingEngineRequestSerializer):
    latitude = serializers.DecimalField(
        max_digits=18,
        decimal_places=15,
        write_only=True,
        allow_null=False,
    )
    longitude = serializers.DecimalField(
        max_digits=18,
        decimal_places=15,
        write_only=True,
        allow_null=False,
    )

from rest_framework import serializers

from api.models import UserAddress
from pricing_engine.api.v1.serializers.request.pricing_engine_request import (
    PricingEngineRequestSerializer,
)


class PricingEngineRequestByUserAddressSerializer(PricingEngineRequestSerializer):
    user_address = serializers.PrimaryKeyRelatedField(
        queryset=UserAddress.objects.all(),
        write_only=True,
        allow_null=False,
    )

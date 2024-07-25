from rest_framework import serializers

from api.models import Product, WasteType


class MatchingEngineRequestByLatLongSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        allow_null=False,
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        write_only=True,
        allow_null=False,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        write_only=True,
        allow_null=False,
    )
    waste_type = serializers.PrimaryKeyRelatedField(
        queryset=WasteType.objects.all(),
        write_only=True,
        allow_null=True,
    )

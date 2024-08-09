from rest_framework import serializers

from api.models import WasteType
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation


class PricingEngineRequestByLatLongSerializer(serializers.Serializer):
    seller_product_seller_location = serializers.PrimaryKeyRelatedField(
        queryset=SellerProductSellerLocation.objects.all(),
        write_only=True,
        allow_null=False,
    )
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
    waste_type = serializers.PrimaryKeyRelatedField(
        queryset=WasteType.objects.all(),
        write_only=True,
        allow_null=True,
    )
    start_date = serializers.DateTimeField(
        write_only=True,
        allow_null=False,
    )
    end_date = serializers.DateTimeField(
        write_only=True,
        allow_null=False,
    )
    times_per_week = serializers.IntegerField(
        write_only=True,
        allow_null=True,
    )

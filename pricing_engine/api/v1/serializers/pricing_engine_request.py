from rest_framework import serializers

from api.models import SellerProductSellerLocation, UserAddress, WasteType


class PricingEngineRequestSerializer(serializers.Serializer):
    seller_product_seller_location = serializers.PrimaryKeyRelatedField(
        queryset=SellerProductSellerLocation.objects.all(),
        write_only=True,
        allow_null=False,
    )
    user_address = serializers.PrimaryKeyRelatedField(
        queryset=UserAddress.objects.all(),
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

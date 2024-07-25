from rest_framework import serializers

from api.models import Product, UserAddress, WasteType


class MatchingEngineRequestSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
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

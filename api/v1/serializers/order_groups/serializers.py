import datetime
from typing import Optional

from rest_framework import serializers
from api.serializers import (
    UserSerializer,
    UserAddressSerializer,
    WasteTypeSerializer,
    TimeSlotSerializer,
    ServiceRecurringFrequencySerializer,
    DayOfWeekSerializer,
    SellerLocationSerializer,
    SellerProductSerializer,
    OrderSerializer,
)
from api.models import OrderGroup, SellerProductSellerLocation


class SellerProductSellerLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller_product = SellerProductSerializer(read_only=True)
    seller_location = SellerLocationSerializer(read_only=True)

    class Meta:
        model = SellerProductSellerLocation
        fields = "__all__"


class OrderGroupListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user = UserSerializer(read_only=True)
    user_address = UserAddressSerializer(read_only=True)
    seller_product_seller_location = SellerProductSellerLocationSerializer(
        read_only=True
    )
    waste_type = WasteTypeSerializer(read_only=True)
    time_slot = TimeSlotSerializer(read_only=True)
    service_recurring_frequency = ServiceRecurringFrequencySerializer(read_only=True)
    preferred_service_days = DayOfWeekSerializer(many=True, read_only=True)
    active = serializers.SerializerMethodField(read_only=True)
    code = serializers.SerializerMethodField(read_only=True)
    orders = OrderSerializer(many=True, read_only=True)
    nearest_order_date = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderGroup
        fields = (
            "id",
            "user",
            "user_address",
            "seller_product_seller_location",
            "waste_type",
            "time_slot",
            "service_recurring_frequency",
            "preferred_service_days",
            "active",
            "created_on",
            "updated_on",
            "is_deleted",
            "access_details",
            "placement_details",
            "delivered_to_street",
            "start_date",
            "end_date",
            "estimated_end_date",
            "take_rate",
            "tonnage_quantity",
            "times_per_week",
            "shift_count",
            "is_delivery",
            "delivery_fee",
            "removal_fee",
            "created_by",
            "updated_by",
            "status",
            "code",
            "orders",
            "agreement",
            "agreement_signed_by",
            "agreement_signed_on",
            "nearest_order_date",
        )

    def get_active(self, obj) -> bool:
        return obj.end_date is None or obj.end_date > datetime.datetime.now().date()

    def get_code(self, obj):
        return obj.get_code

    def get_nearest_order_date(self, obj) -> Optional[datetime.date]:
        return obj.nearest_order.end_date if obj.nearest_order else None


class OrderGroupNewTransactionRequestSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    schedule_window = serializers.ChoiceField(
        default="Anytime (7am-4pm)",
        choices=["Anytime (7am-4pm)", "Morning (7am-11am)", "Afternoon (12pm-4pm)"],
    )


class OrderGroupAccessDetailsRequestSerializer(serializers.Serializer):
    access_details = serializers.CharField(required=True)


class OrderGroupPlacementDetailsRequestSerializer(serializers.Serializer):
    placement_details = serializers.CharField(required=True)
    delivered_to_street = serializers.BooleanField(required=True)

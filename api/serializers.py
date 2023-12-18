import stripe
from django.conf import settings
from rest_framework import serializers

from .models import *

stripe.api_key = settings.STRIPE_SECRET_KEY


class SellerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    has_listings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Seller
        fields = "__all__"

    def get_has_listings(self, obj):
        return obj.seller_products.count() > 0


class SellerLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller = SellerSerializer(read_only=True)
    seller_id = serializers.PrimaryKeyRelatedField(
        queryset=Seller.objects.all(), source="seller", write_only=True
    )

    class Meta:
        model = SellerLocation
        fields = "__all__"


class UserAddressTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserAddressType
        fields = "__all__"


class UserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserAddress
        fields = "__all__"
        validators = []


class UserGroupLegalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, read_only=True
    )
    longitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, read_only=True
    )

    class Meta:
        model = UserGroupLegal
        fields = "__all__"


class UserGroupSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller = SellerSerializer(read_only=True)
    seller_id = serializers.PrimaryKeyRelatedField(
        queryset=Seller.objects.all(), source="seller", write_only=True, allow_null=True
    )
    legal = UserGroupLegalSerializer(read_only=True)
    credit_limit_utilized = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserGroup
        fields = "__all__"

    def get_credit_limit_utilized(self, obj: UserGroup):
        return obj.credit_limit_used()


class UserGroupCreditApplicationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupCreditApplication
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user_id = serializers.CharField(required=False, allow_null=True)
    user_group = UserGroupSerializer(read_only=True)
    user_group_id = serializers.PrimaryKeyRelatedField(
        queryset=UserGroup.objects.all(),
        source="user_group",
        write_only=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = "__all__"
        validators = []


class UserUserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserUserAddress
        fields = "__all__"


class UserSellerReviewSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )
    seller = SellerSerializer(read_only=True)
    seller_id = serializers.PrimaryKeyRelatedField(
        queryset=Seller.objects.all(), source="seller", write_only=True
    )

    class Meta:
        model = UserSellerReview
        fields = "__all__"


class UserSellerReviewAggregateSerializer(serializers.Serializer):
    seller_name = serializers.CharField()
    rating_avg = serializers.FloatField()
    review_count = serializers.IntegerField()


class AddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = AddOn
        fields = "__all__"


class AddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    add_on = AddOnSerializer(read_only=True)

    class Meta:
        model = AddOnChoice
        fields = "__all__"


class DisposalLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = DisposalLocation
        fields = "__all__"


class DisposalLocationWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = DisposalLocationWasteType
        fields = "__all__"


class MainProductAddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductAddOn
        fields = "__all__"


class MainProductCategoryInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductCategoryInfo
        fields = "__all__"


class MainProductCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductCategory
        fields = "__all__"


class MainProductInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductInfo
        fields = "__all__"


class MainProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    main_product_category = MainProductCategorySerializer(read_only=True)

    class Meta:
        model = MainProduct
        fields = "__all__"


class MainProductWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductWasteType
        fields = "__all__"


class OrderLineItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderLineItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    order_line_items = OrderLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    # def get_status(self, obj):
    #     return stripe.Invoice.retrieve(
    #     obj.stripe_invoice_id,
    #     ).status if obj.stripe_invoice_id and obj.stripe_invoice_id != "" else None


class OrderLineItemTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderLineItemType
        fields = "__all__"


class OrderDisposalTicketSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderDisposalTicket
        fields = "__all__"


class DayOfWeekSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = DayOfWeek
        fields = "__all__"


class TimeSlotSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = TimeSlot
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    order_number = serializers.CharField(required=False)

    class Meta:
        model = Subscription
        fields = "__all__"


class PayoutSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Payout
        fields = "__all__"


class ProductAddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    add_on_choice = AddOnChoiceSerializer(read_only=True)

    class Meta:
        model = ProductAddOnChoice
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    main_product = MainProductSerializer(read_only=True)
    product_add_on_choices = ProductAddOnChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class SellerProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller = SellerSerializer(read_only=True)
    seller_id = serializers.PrimaryKeyRelatedField(
        queryset=Seller.objects.all(), source="seller", write_only=True
    )
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True
    )

    class Meta:
        model = SellerProduct
        fields = "__all__"


class SellerProductSellerLocationServiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerProductSellerLocationService
        fields = "__all__"


class ServiceRecurringFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = ServiceRecurringFrequency
        fields = "__all__"


class MainProductServiceRecurringFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductServiceRecurringFrequency
        fields = "__all__"


class SellerProductSellerLocationServiceRecurringFrequencySerializer(
    serializers.ModelSerializer
):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerProductSellerLocationServiceRecurringFrequency
        fields = "__all__"


class SellerProductSellerLocationRentalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerProductSellerLocationRental
        fields = "__all__"


class SellerProductSellerLocationMaterialWasteTypeSerializer(
    serializers.ModelSerializer
):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerProductSellerLocationMaterialWasteType
        fields = "__all__"


class SellerProductSellerLocationMaterialSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    waste_types = SellerProductSellerLocationMaterialWasteTypeSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = SellerProductSellerLocationMaterial
        fields = "__all__"

    def create(self, validated_data):
        waste_types = validated_data.pop("waste_types")

        # Create SellerProductSellerLocation.
        material = SellerProductSellerLocationMaterial.objects.create(**validated_data)

        # Create waste types.
        for waste_type in waste_types:
            SellerProductSellerLocationMaterialWasteType.objects.create(
                seller_product_seller_location_material=material, **waste_type
            )

        return material

    def update(self, instance, validated_data):
        waste_types = validated_data.pop("waste_types")

        # Update SellerProductSellerLocation.
        instance.save()

        # Delete the old waste types.
        for waste_type in instance.waste_types.all():
            waste_type.delete()

        # Update waste types.
        for waste_type in waste_types:
            SellerProductSellerLocationMaterialWasteType.objects.update_or_create(
                **waste_type
            )

        return instance


class SellerProductSellerLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller_product = SellerProductSerializer(read_only=True)
    seller_product_id = serializers.PrimaryKeyRelatedField(
        queryset=SellerProduct.objects.all(), source="seller_product", write_only=True
    )
    seller_location = SellerLocationSerializer(read_only=True)
    seller_location_id = serializers.PrimaryKeyRelatedField(
        queryset=SellerLocation.objects.all(), source="seller_location", write_only=True
    )
    service = SellerProductSellerLocationServiceSerializer(read_only=True)
    material = SellerProductSellerLocationMaterialSerializer(read_only=True)
    rental = SellerProductSellerLocationRentalSerializer(read_only=True)

    class Meta:
        model = SellerProductSellerLocation
        fields = "__all__"


class SellerInvoicePayableSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerInvoicePayable
        fields = "__all__"


class SellerInvoicePayableLineItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = SellerInvoicePayableLineItem
        fields = "__all__"


class WasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = WasteType
        fields = "__all__"


class OrderGroupServiceSerializer(serializers.ModelSerializer):
    order_group = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderGroupService
        fields = "__all__"


class OrderGroupRentalSerializer(serializers.ModelSerializer):
    order_group = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderGroupRental
        fields = "__all__"


class OrderGroupMaterialSerializer(serializers.ModelSerializer):
    order_group = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = OrderGroupMaterial
        fields = "__all__"


class OrderGroupSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )
    user_address = UserAddressSerializer(read_only=True)
    user_address_id = serializers.PrimaryKeyRelatedField(
        queryset=UserAddress.objects.all(), source="user_address", write_only=True
    )
    seller_product_seller_location = SellerProductSellerLocationSerializer(
        read_only=True
    )
    seller_product_seller_location_id = serializers.PrimaryKeyRelatedField(
        queryset=SellerProductSellerLocation.objects.all(),
        source="seller_product_seller_location",
        write_only=True,
    )
    waste_type = WasteTypeSerializer(read_only=True)
    waste_type_id = serializers.PrimaryKeyRelatedField(
        queryset=WasteType.objects.all(),
        source="waste_type",
        write_only=True,
        allow_null=True,
    )
    time_slot = TimeSlotSerializer(read_only=True)
    time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.all(),
        source="time_slot",
        write_only=True,
        allow_null=True,
    )
    service_recurring_frequency = ServiceRecurringFrequencySerializer(read_only=True)
    service_recurring_frequency_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceRecurringFrequency.objects.all(),
        source="service_recurring_frequency",
        write_only=True,
        allow_null=True,
    )
    preferred_service_days = DayOfWeekSerializer(many=True, read_only=True)
    preferred_service_day_ids = serializers.PrimaryKeyRelatedField(
        queryset=DayOfWeek.objects.all(),
        many=True,
        source="preferred_service_days",
        write_only=True,
    )
    service = OrderGroupServiceSerializer(allow_null=True)
    rental = OrderGroupRentalSerializer(allow_null=True)
    material = OrderGroupMaterialSerializer(allow_null=True)
    orders = OrderSerializer(many=True, read_only=True)
    active = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderGroup
        fields = "__all__"

    def create(self, validated_data):
        service_data = validated_data.pop("service")
        rental_data = validated_data.pop("rental")
        material_data = validated_data.pop("material")

        # Create order group.
        preferred_service_days = validated_data.pop("preferred_service_days")
        order_group = OrderGroup.objects.create(**validated_data)
        order_group.preferred_service_days.set(preferred_service_days)

        # Create service, rental, and material.
        if service_data:
            OrderGroupService.objects.create(order_group=order_group, **service_data)
        if rental_data:
            OrderGroupRental.objects.create(order_group=order_group, **rental_data)
        if material_data:
            OrderGroupMaterial.objects.create(order_group=order_group, **material_data)

        return order_group

    def update(self, instance, validated_data):
        # Remove nested data.
        validated_data.pop("service")
        validated_data.pop("rental")
        validated_data.pop("material")

        preferred_service_days = validated_data.pop("preferred_service_days")
        instance.save()
        instance.preferred_service_days.set(preferred_service_days)
        return instance

    def get_active(self, obj):
        return obj.end_date is None or obj.end_date > datetime.datetime.now().date()

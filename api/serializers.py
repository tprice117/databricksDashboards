import datetime
import logging
from typing import Literal, Union

import stripe
from django.conf import settings
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers

from admin_policies.api.v1.serializers import (
    UserGroupPolicyInvitationApprovalSerializer,
    UserGroupPolicyMonthlyLimitSerializer,
    UserGroupPolicyPurchaseApprovalSerializer,
)
from notifications.utils.internal_email import send_email_on_new_signup

from .models import (
    AddOn,
    AddOnChoice,
    DayOfWeek,
    DisposalLocation,
    DisposalLocationWasteType,
    MainProduct,
    MainProductAddOn,
    MainProductCategory,
    MainProductCategoryInfo,
    MainProductInfo,
    MainProductServiceRecurringFrequency,
    MainProductWasteType,
    Order,
    OrderDisposalTicket,
    OrderGroup,
    OrderGroupMaterial,
    OrderGroupRental,
    OrderGroupService,
    OrderLineItem,
    OrderLineItemType,
    Payout,
    Product,
    ProductAddOnChoice,
    Seller,
    SellerInvoicePayable,
    SellerInvoicePayableLineItem,
    SellerLocation,
    SellerProduct,
    SellerProductSellerLocation,
    SellerProductSellerLocationMaterial,
    SellerProductSellerLocationMaterialWasteType,
    SellerProductSellerLocationRental,
    SellerProductSellerLocationService,
    SellerProductSellerLocationServiceRecurringFrequency,
    ServiceRecurringFrequency,
    Subscription,
    TimeSlot,
    User,
    UserAddress,
    UserAddressType,
    UserGroup,
    UserGroupBilling,
    UserGroupCreditApplication,
    UserGroupLegal,
    UserSellerReview,
    UserUserAddress,
    WasteType,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class SellerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    has_listings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Seller
        fields = "__all__"

    def get_has_listings(self, obj) -> bool:
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
    stripe_customer_id = serializers.CharField(required=False, allow_null=True)
    allow_saturday_delivery = serializers.BooleanField(required=False, allow_null=True)
    allow_sunday_delivery = serializers.BooleanField(required=False, allow_null=True)

    class Meta:
        model = UserAddress
        fields = "__all__"
        validators = []


class UserGroupBillingSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, read_only=True
    )
    longitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, read_only=True
    )

    class Meta:
        model = UserGroupBilling
        fields = "__all__"


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
        fields = [
            "id",
            "name",
            "doing_business_as",
            "structure",
            "industry",
            "street",
            "city",
            "state",
            "postal_code",
            "country",
            "latitude",
            "longitude",
        ]


class UserGroupCreditApplicationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupCreditApplication
        fields = "__all__"
        read_only_fields = ["status"]


class UserGroupSerializer(WritableNestedModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    seller = SellerSerializer(read_only=True)
    seller_id = serializers.PrimaryKeyRelatedField(
        queryset=Seller.objects.all(), source="seller", write_only=True, allow_null=True
    )
    legal = UserGroupLegalSerializer(
        allow_null=True,
    )
    credit_applications = UserGroupCreditApplicationSerializer(
        many=True,
        read_only=True,
    )
    credit_limit_utilized = serializers.SerializerMethodField(read_only=True)
    net_terms = serializers.IntegerField(
        required=False,
        default=UserGroup.NetTerms.IMMEDIATELY,
        allow_null=True,
    )
    invoice_at_project_completion = serializers.BooleanField(
        required=False,
        default=False,
        allow_null=True,
    )
    share_code = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    policy_invitation_approvals = UserGroupPolicyInvitationApprovalSerializer(
        many=True,
        required=False,
        allow_null=True,
    )
    policy_monthly_limit = UserGroupPolicyMonthlyLimitSerializer(
        required=False,
        allow_null=True,
    )
    policy_purchase_approvals = UserGroupPolicyPurchaseApprovalSerializer(
        many=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UserGroup
        fields = "__all__"

    def create(self, validated_data):
        # Check for null net_terms and set default if needed
        if validated_data.get("net_terms") is None:
            validated_data["net_terms"] = UserGroup.NetTerms.IMMEDIATELY
        if validated_data.get("invoice_at_project_completion") is None:
            validated_data["invoice_at_project_completion"] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Check for null net_terms and set default if needed
        if validated_data.get("net_terms") is None:
            validated_data["net_terms"] = UserGroup.NetTerms.IMMEDIATELY
        if validated_data.get("invoice_at_project_completion") is None:
            validated_data["invoice_at_project_completion"] = False
        return super().update(instance, validated_data)

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_credit_limit_utilized(self, obj: UserGroup):
        return obj.credit_limit_used()


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    user_group = UserGroupSerializer(read_only=True)
    user_group_id = serializers.PrimaryKeyRelatedField(
        queryset=UserGroup.objects.all(),
        required=False,
        source="user_group",
        write_only=True,
        allow_null=True,
    )

    def create(self, validated_data):
        """
        Create and return a new `User` instance, given the validated data.
        """
        new_user = User.objects.create(**validated_data)
        # Send internal email to notify team.
        if settings.ENVIRONMENT == "TEST":
            # Only send this if the creation is from Auth0. Auth0 will send in the token in user_id.
            if validated_data.get("user_id", None) is not None:
                send_email_on_new_signup(
                    new_user.email, created_by_downstream_team=False
                )
        else:
            logger.info(
                f"UserSerializer.create: [New User Signup]-[{validated_data}]",
            )
        return new_user

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
    main_product_category_infos = MainProductCategoryInfoSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = MainProductCategory
        fields = "__all__"
        extra_fields = ["main_product_category_infos"]

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(MainProductCategorySerializer, self).get_field_names(
            declared_fields, info
        )

        if getattr(self.Meta, "extra_fields", None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields


class MainProductInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = MainProductInfo
        fields = "__all__"


class MainProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    main_product_category = MainProductCategorySerializer(read_only=True)
    main_product_infos = MainProductInfoSerializer(many=True, read_only=True)

    class Meta:
        model = MainProduct
        fields = "__all__"
        extra_fields = ["main_product_infos"]

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(MainProductSerializer, self).get_field_names(
            declared_fields, info
        )

        if getattr(self.Meta, "extra_fields", None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields


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
    order_type = serializers.SerializerMethodField(read_only=True)
    service_date = serializers.SerializerMethodField(read_only=True)
    customer_price = serializers.SerializerMethodField(read_only=True)
    seller_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    @extend_schema_field(
        Union[
            Literal[
                Order.Type.DELIVERY,
                Order.Type.ONE_TIME,
                Order.Type.REMOVAL,
                Order.Type.SWAP,
                Order.Type.AUTO_RENEWAL,
            ],
            None,
        ]
    )
    def get_order_type(self, obj: Order):
        return obj.order_type

    @extend_schema_field(OpenApiTypes.DATE)
    def get_service_date(self, obj: Order):
        return obj.end_date

    def get_customer_price(self, obj: Order):
        return obj.customer_price()

    def get_seller_price(self, obj: Order):
        return obj.seller_price()

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
        print("-------------")
        print(validated_data)
        print("-------------")
        print(instance)
        # Remove nested data.
        if "service" in validated_data:
            validated_data.pop("service")
        if "rental" in validated_data:
            validated_data.pop("rental")
        if "material" in validated_data:
            validated_data.pop("material")

        if "preferred_service_days" in validated_data:
            preferred_service_days = validated_data.pop("preferred_service_days")
            super(OrderGroupSerializer, self).update(instance, validated_data)
            instance.preferred_service_days.set(preferred_service_days)
        else:
            super(OrderGroupSerializer, self).update(instance, validated_data)
        return instance

    def get_active(self, obj) -> bool:
        return obj.end_date is None or obj.end_date > datetime.datetime.now().date()

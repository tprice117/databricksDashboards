from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from typing import Literal, Union

from api.models import Order, MainProduct, User
from api.serializers import (
    UserAddressSerializer,
)
from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
    PricingEngineResponseSerializer,
)


class CartItemOrderUserSerializer(serializers.ModelSerializer):
    """Serializer for the user who created the order with only essential fields"""

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email"]


class CartItemOrderSerializer(serializers.ModelSerializer):
    """Serializer for the cart item order with some fields removed"""

    service_date = serializers.SerializerMethodField(read_only=True)
    created_by = CartItemOrderUserSerializer(read_only=True)
    order_type = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)

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

    @extend_schema_field(PricingEngineResponseSerializer)
    def get_price(self, obj):
        # Expensive operation
        return obj.get_price()

    def get_service_date(self, obj):
        return obj.end_date


class CartItemMainProductSerializer(serializers.ModelSerializer):
    """Serializer for the main product of the cart item with only essential fields"""

    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MainProduct
        fields = ["id", "name", "image"]

    def get_image(self, obj):
        if obj.image_del:
            return obj.image_del
        elif obj.main_product_category.icon:
            return obj.main_product_category.icon.url
        return None


class CartItemSerializer(serializers.Serializer):
    """Serializer for the cart item

    Attributes:
        main_product: The main product of the cart item
        order: The order of the cart item
        customer_price: The pre-tax total price for the item
    """

    main_product = CartItemMainProductSerializer(read_only=True)
    order = CartItemOrderSerializer(read_only=True)

    # customer_price is pre-tax total price for the item
    customer_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )


class CartGroupSerializer(serializers.Serializer):
    """Serializer for the cart group (based on UserAddress)

    Attributes:
        address: The address of the cart group
        items: The list of CartItems in the cart group
        total: The total price of the cart group
        count: The total number of items in the cart group
        show_quote: Whether to show the quote
    """

    address = UserAddressSerializer(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    count = serializers.IntegerField(read_only=True)
    show_quote = serializers.BooleanField(read_only=True)


class CartSerializer(serializers.Serializer):
    """Serializer for the cart item

    Attributes:
        cart: The list of CartGroups
        subtotal: The total price of the cart
        cart_count: The total number of items in the cart
    """

    cart = CartGroupSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cart_count = serializers.IntegerField(read_only=True)

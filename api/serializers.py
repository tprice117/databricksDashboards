from rest_framework import serializers
from .models import *

class SellerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    has_listings = serializers.SerializerMethodField(read_only=True)
    
    def get_has_listings(self, obj):
       return obj.seller_products.count() > 0

    class Meta:
        model = Seller
        fields = "__all__"
        
class UserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = UserAddress
        fields = "__all__"
        validators = []
    
class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = User
        fields = "__all__"
        validators = []
        
class AddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AddOnChoice
        fields = "__all__"
        
class AddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AddOn
        fields = "__all__"
        
class MainProductAddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductAddOn
        fields = "__all__"

class MainProductCategoryInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductCategoryInfo
        fields = "__all__"

class MainProductCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductCategory
        fields = "__all__"

class MainProductInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductInfo
        fields = "__all__"

class MainProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProduct
        fields = "__all__"

class MainProductWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductWasteType
        fields = "__all__"

class OrderDetailsSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderDetails
        fields = "__all__"

class OrderDetailsLineItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderDetailsLineItem
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    order_number = serializers.CharField(required=False)
    class Meta:
        model = Order
        fields = "__all__"

class ProductAddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductAddOnChoice
        fields = "__all__"

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Product
        fields = "__all__"
        
class SellerProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProduct
        fields = "__all__"

class WasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = WasteType
        fields = "__all__"
















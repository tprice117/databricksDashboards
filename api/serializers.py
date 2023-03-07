from django.conf import settings
from rest_framework import serializers
from .models import *
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

class SellerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    has_listings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Seller
        fields = "__all__"
    
    def get_has_listings(self, obj):
       return obj.seller_products.count() > 0
    
class SellerLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerLocation
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

class UserUserAddressSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = UserUserAddress
        fields = "__all__"

class UserSellerReviewSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = UserSellerReview
        fields = "__all__"
        
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
    # status = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = OrderDetails
        fields = "__all__"

    # def get_status(self, obj):
    #     return stripe.Invoice.retrieve(
    #         obj.stripe_invoice_id,
    #     ).status if obj.stripe_invoice_id and obj.sstripe_invoice_id != "" else None

class OrderDetailsLineItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderDetailsLineItem
        fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    order_number = serializers.CharField(required=False)
    class Meta:
        model = Subscription
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

class SellerProductSellerLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    available_quantity = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = SellerProductSellerLocation
        fields = "__all__"
    
    def get_available_quantity(self, obj):
        #order_detail_count = OrderDetails.objects.filter(
        #seller_product_seller_location=obj.id,
        #invoice_status__in=["Paid", "Open"] TODO: need to grab these statuses from the Stripe API
        #).count()
        return 0
        #obj.total_inventory - order_detail_count

class WasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = WasteType
        fields = "__all__"

class DevEnvironTestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = DevEnvironTest
        fields = "__all__"















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

class UserAddressTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = UserAddressType
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

class UserGroupSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = UserGroup
        fields = "__all__"

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

class UserSellerReviewAggregateSerializer(serializers.Serializer):
    seller_name = serializers.CharField()
    rating_avg = serializers.FloatField()
    review_count = serializers.IntegerField()
       
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

class DisposalLocationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = DisposalLocation
        fields = "__all__"

class DisposalLocationWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = DisposalLocationWasteType
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

class OrderGroupSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderGroup
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    
    class Meta:
        model = Order
        fields = "__all__"

    # def get_status(self, obj):
    #     return stripe.Invoice.retrieve(
    #     obj.stripe_invoice_id,
    #     ).status if obj.stripe_invoice_id and obj.stripe_invoice_id != "" else None

class OrderLineItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderLineItem
        fields = "__all__"

class OrderLineItemTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderLineItemType
        fields = "__all__"
    
class OrderDisposalTicketSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = OrderDisposalTicket
        fields = "__all__"

class DayOfWeekSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = DayOfWeek
        fields = "__all__"

class TimeSlotSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = TimeSlot
        fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    order_number = serializers.CharField(required=False)
    class Meta:
        model = Subscription
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
        #order_detail_count = Order.objects.filter(
        #seller_product_seller_location=obj.id,
        #invoice_status__in=["Paid", "Open"] TODO: need to grab these statuses from the Stripe API
        #).count()
        return 0
        #obj.total_inventory - order_detail_count

class SellerProductSellerLocationServiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductSellerLocationService
        fields = "__all__"

class ServiceRecurringFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ServiceRecurringFrequency
        fields = "__all__"

class MainProductServiceRecurringFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductServiceRecurringFrequency
        fields = "__all__"

class SellerProductSellerLocationServiceRecurringFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductSellerLocationServiceRecurringFrequency
        fields = "__all__"

class SellerProductSellerLocationRentalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductSellerLocationRental
        fields = "__all__"

class SellerProductSellerLocationMaterialSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductSellerLocationMaterial
        fields = "__all__"

class SellerProductSellerLocationMaterialWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductSellerLocationMaterialWasteType
        fields = "__all__"

class WasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = WasteType
        fields = "__all__"

















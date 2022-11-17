from rest_framework import serializers
from .models import *

class AccountContactSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AccountContactRelation
        fields = "__all__"
        
class AccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Account
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

class ContactSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Contact
        fields = "__all__"

class DisposalFeeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = DisposalFee
        fields = "__all__"

class LocationZoneSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = LocationZone
        fields = "__all__"
        
class MainProductAddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductAddOn
        fields = "__all__"

class MainProductCategoryInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductCategoryInfo
        fields = "__all__"

class MainProductCategorySerializer(serializers.ModelSerializer):
    main_product_category_infos = serializers.SerializerMethodField(read_only=True)
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductCategory
        fields = "__all__"

    def get_main_product_category_infos(self, main_product_category):
        return MainProductCategoryInfoSerializer(ProductCategoryInfo.objects.filter(product_category=main_product_category), many=True).data

class MainProductInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductInfo
        fields = "__all__"

class MainProductSerializer(serializers.ModelSerializer):
    main_product_infos = serializers.SerializerMethodField(read_only=True)
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProduct
        fields = "__all__"
    
    def get_main_product_infos(self, main_product):
        return MainProductInfoSerializer(MainProductInfo.objects.filter(main_product=main_product), many=True).data


class MainProductWasteTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductWasteType
        fields = "__all__"

class OpportunitySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Opportunity
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    order_number = serializers.CharField(required=False)
    class Meta:
        model = Order
        fields = "__all__"

class PostalCodeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = PostalCode
        fields = "__all__"

class PriceBookEntrySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = PricebookEntry
        fields = "__all__"

class PriceBookSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Pricebook2
        fields = "__all__"

class ProductAddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductAddOnChoice
        fields = "__all__"

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Product2
        fields = "__all__"

class SellerProductLocationZoneSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = SellerProductLocationZone
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
















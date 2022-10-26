from rest_framework import serializers
from .models import *

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    order_number = serializers.CharField(required=False)
    class Meta:
        model = Order
        fields = "__all__"

class ContactSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Contact
        fields = "__all__"

class AccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Account
        fields = "__all__"
        validators = []

class AccountContactSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AccountContactRelation
        fields = "__all__"

class OpportunitySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Opportunity
        fields = "__all__"

class MainProductCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductCategory
        fields = "__all__"

class ProductCategoryInfoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductCategoryInfo
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

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Product2
        fields = "__all__"

# class MainProductFrequencySerializer(serializers.ModelSerializer):
#     id = serializers.CharField(required=False)
#     class Meta:
#         model = MainProductFrequency
#         fields = "__all__"

class PriceBookSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Pricebook2
        fields = "__all__"

class PriceBookEntrySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = PricebookEntry
        fields = "__all__"

class MainProductAddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductAddOn
        fields = "__all__"

class ProductAddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductAddOnChoice
        fields = "__all__"

class AddOnSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AddOn
        fields = "__all__"

class AddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = AddOnChoice
        fields = "__all__"

class LocationZoneSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = LocationZone
        fields = "__all__"

class PostalCodeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = PostalCode
        fields = "__all__"


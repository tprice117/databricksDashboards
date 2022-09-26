from rest_framework import serializers
from .models import *

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Order
        fields = "__all__"

class AccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Account
        fields = "__all__"

class OpportunitySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = Opportunity
        fields = "__all__"

class ProductCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = ProductCategory
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

class MainProductFrequencySerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductFrequency
        fields = "__all__"

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

class MainProductAddOnChoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False)
    class Meta:
        model = MainProductAddOnChoice
        fields = "__all__"

# class ContactSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Contact
#         exclude=("scrapper",)

# class AddressSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Address
#         exclude=("scrapper",)

# class VehicleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Vehicle
#         exclude=("scrapper",)

# class ScrapperSerializer(serializers.ModelSerializer):
#   contact = ContactSerializer()
#   address = AddressSerializer()
#   vehicle = VehicleSerializer()
#   class Meta:
#     model = Scrapper
#     fields = "__all__"

#   # Now override the default create method to create a new object.
#   # A similar overriding can be done for update as well.
#   def create(self, validated_data):
#       scrapper = Scrapper.objects.create(type = validated_data.pop('type'))
#       Contact.objects.create(scrapper=scrapper, **validated_data.pop("contact"))
#       Address.objects.create(scrapper=scrapper, **validated_data.pop('address'))
#       Vehicle.objects.create(scrapper=scrapper, **validated_data.pop('vehicle'))
#       return scrapper

#   # Now override the default create method to create a new object.
#   # A similar overriding can be done for update as well.
#   def update(self, instance, validated_data):
#       instance.type = validated_data.get('type', instance.type)
#       instance.save()

#       contact_old = Contact.objects.get(pk=instance.id, scrapper=instance)
#       contact_new = ContactSerializer(contact_old, data=validated_data.pop("contact"))
#       if (contact_new.is_valid()):
#         contact_new.save()

#       address_old = Address.objects.get(pk=instance.id, scrapper=instance)
#       address_new = AddressSerializer(address_old, data=validated_data.pop("address"))
#       if (address_new.is_valid()):
#         address_new.save()

#       vehicle_old = Vehicle.objects.get(pk=instance.id, scrapper=instance)
#       vehicle_new = VehicleSerializer(vehicle_old, data=validated_data.pop("vehicle"))
#       if (vehicle_new.is_valid()):
#         vehicle_new.save()
#       return instance
    


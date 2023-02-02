from django.contrib import admin
from .models import *

# Register your models here.
# class ContactInline(admin.StackedInline):
#     model = Contact

# class AddressInline(admin.StackedInline):
#     model = Address

# class VehicleInline(admin.StackedInline):
#     model = Vehicle

# class ScrapperAdmin(admin.ModelAdmin):
#     inlines = [ContactInline, AddressInline, VehicleInline]

# Register your models here.
admin.site.register(AccountContactRelation)
admin.site.register(Account)
admin.site.register(AddOnChoice)
admin.site.register(AddOn)
admin.site.register(Contact)
admin.site.register(DisposalFee)
admin.site.register(LocationZone)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategoryInfo)
admin.site.register(MainProductCategory)
admin.site.register(MainProductInfo)
admin.site.register(MainProduct)
admin.site.register(MainProductWasteType)
admin.site.register(Opportunity)
admin.site.register(Order)
admin.site.register(PostalCode)
admin.site.register(Pricebook)
admin.site.register(ProductAddOnChoice)
admin.site.register(Product)
admin.site.register(SellerProductLocationZone)
admin.site.register(SellerProduct)
admin.site.register(WasteType)

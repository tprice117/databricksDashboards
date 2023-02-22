from django.contrib import admin
from .models import *
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group

class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo

class MainProductInline(admin.TabularInline):
    model = MainProduct

class MainProductCategoryAdmin(admin.ModelAdmin):
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]

class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo

class ProductInline(admin.TabularInline):
    model = Product

class MainProductAdmin(admin.ModelAdmin):
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]

class SellerProductInline(admin.TabularInline):
    model = SellerProduct

class SellerAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductInline,
    ]

# Register your models here.
admin.site.register(Seller)
admin.site.register(UserAddress)
admin.site.register(User)
admin.site.register(AddOnChoice)
admin.site.register(AddOn)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategory, MainProductCategoryAdmin)
admin.site.register(MainProduct, MainProductAdmin)
admin.site.register(MainProductWasteType)
admin.site.register(OrderDetails)
admin.site.register(OrderDetailsLineItem)
admin.site.register(Order)
admin.site.register(ProductAddOnChoice)
admin.site.register(WasteType)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)

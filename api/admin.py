from django.contrib import admin
from .models import *
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group

class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo
    fields = ('name',)
    readonly_fields = ('name',)
    show_change_link = True
    extra=0

class MainProductInline(admin.TabularInline):
    model = MainProduct
    fields = ('name',)
    readonly_fields = ('name',)
    show_change_link = True
    extra=0

class MainProductCategoryAdmin(admin.ModelAdmin):
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]

class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo
    fields = ('name',)
    readonly_fields = ('name',)
    show_change_link = True
    extra=0

class ProductInline(admin.TabularInline):
    model = Product
    fields = ('product_code', 'description')
    readonly_fields = ('product_code', 'description')
    show_change_link = True
    extra=0

class MainProductAdmin(admin.ModelAdmin):
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]

class SellerProductInline(admin.TabularInline):
    model = SellerProduct
    fields = ('product',)
    readonly_fields = ('product',)
    show_change_link = True
    extra=0

class SellerAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductInline,
    ]

class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    search_fields = ["name", "street"]

class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["email", "first_name", "last_name"]

class OrderAdmin(admin.ModelAdmin):
    model = Order
    autocomplete_fields = ["user_address", "user"]

# Register your models here.
admin.site.register(Seller, SellerAdmin)
admin.site.register(SellerLocation)
admin.site.register(SellerProduct)
admin.site.register(SellerProductSellerLocation)
admin.site.register(UserAddress, UserAddressAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserUserAddress)
admin.site.register(AddOnChoice)
admin.site.register(AddOn)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategory, MainProductCategoryAdmin)
admin.site.register(MainProductCategoryInfo)
admin.site.register(MainProduct, MainProductAdmin)
admin.site.register(MainProductInfo)
admin.site.register(MainProductWasteType)
admin.site.register(Product)
admin.site.register(OrderGroup)
admin.site.register(Order, OrderAdmin)
admin.site.register(ProductAddOnChoice)
admin.site.register(WasteType)
admin.site.register(DisposalLocation)
admin.site.register(DisposalLocationWasteType)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)

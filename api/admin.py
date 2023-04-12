from django.contrib import admin
from .models import *
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group
from .forms import *

# Inlines.
class AddOnChoiceInline(admin.TabularInline):
    model = AddOnChoice
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductInline(admin.TabularInline):
    model = MainProduct
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo
    fields = ('name',)
    show_change_link = True
    extra=0

class ProductInline(admin.TabularInline):
    model = Product
    fields = ('product_code', 'description')
    show_change_link = True
    extra=0

class ProductAddOnChoiceInline(admin.TabularInline):
    model = ProductAddOnChoice
    fields = ('name', 'product', 'add_on_choice')
    show_change_link = True
    extra=0

class SellerLocationInline(admin.TabularInline):
    model = SellerLocation
    fields = ('name',)
    show_change_link = True
    extra=0

class SellerProductInline(admin.TabularInline):
    model = SellerProduct
    fields = ('product',)
    show_change_link = True
    extra=0

class SellerProductSellerLocationInline(admin.TabularInline):
    model = SellerProductSellerLocation
    fields = ('seller_product', 'rate', 'total_inventory')
    show_change_link = True
    extra=0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(SellerProductSellerLocationInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'seller_product':
            if request._obj_ is not None:
                print(request._obj_)
                print(field.queryset)
                field.queryset = field.queryset.filter(seller = request._obj_.seller)  
            else:
                field.queryset = field.queryset.none()
        return field




class AddOnChoiceAdmin(admin.ModelAdmin):
    search_fields = ["name", "add_on__name"]
    list_display = ('name', 'add_on')

class AddOnAdmin(admin.ModelAdmin):
    inlines = [
        AddOnChoiceInline,
    ]

class MainProductCategoryAdmin(admin.ModelAdmin):
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]

class ProductAdmin(admin.ModelAdmin):
    search_fields = ["description", "main_product__name"]
    list_display = ('description', 'main_product')
    inlines = [
        ProductAddOnChoiceInline,
    ]

class MainProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product_category__name"]
    list_display = ('name', 'main_product_category', 'sort')
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]

class MainProductInfoAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product__name"]
    list_display = ('name', 'main_product')
    
class SellerAdmin(admin.ModelAdmin):
    form =  OpenDaysAdminForm
    inlines = [
        SellerProductInline,
        SellerLocationInline,
    ]

class SellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["name", "seller__name"]
    list_display = ('name', 'seller')
    inlines = [
        SellerProductSellerLocationInline,
    ]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SellerLocationAdmin, self).get_form(request, obj, **kwargs)
    
class SellerProductAdmin(admin.ModelAdmin):
    search_fields = ["product__description", "seller__name"]
    list_display = ('product', 'seller')

class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    search_fields = ["name", "street"]

class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["email", "first_name", "last_name"]

class OrderAdmin(admin.ModelAdmin):
    model = Order
    autocomplete_fields = ["user_address", "user"]
    search_fields = ["user__email", 'user_address', 'seller_product_seller_location']
    list_display = ('user', 'user_address', 'seller_product_seller_location', 'start_date', 'end_date')

class MainProductWasteTypeAdmin(admin.ModelAdmin):
    model = UserAddress
    search_fields = ["main_product__name", "waste_type__name"]

# Register your models here.
admin.site.register(Seller, SellerAdmin)
admin.site.register(SellerLocation, SellerLocationAdmin)
admin.site.register(SellerProduct, SellerProductAdmin)
admin.site.register(SellerProductSellerLocation)
admin.site.register(UserAddress, UserAddressAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserUserAddress)
admin.site.register(AddOnChoice, AddOnChoiceAdmin)
admin.site.register(AddOn, AddOnAdmin)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategory, MainProductCategoryAdmin)
admin.site.register(MainProductCategoryInfo)
admin.site.register(MainProduct, MainProductAdmin)
admin.site.register(MainProductInfo, MainProductInfoAdmin)
admin.site.register(MainProductWasteType, MainProductWasteTypeAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(OrderGroup)
admin.site.register(Order, OrderAdmin)
admin.site.register(ProductAddOnChoice)
admin.site.register(WasteType)
admin.site.register(DisposalLocation)
admin.site.register(DisposalLocationWasteType)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)

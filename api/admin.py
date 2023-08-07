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

class OrderInline(admin.TabularInline):
    model = Order
    fields = ('start_date', 'end_date', 'service_date', 'submitted_on')
    show_change_link = True
    extra=0

class SubscriptionInline(admin.StackedInline):
    model = Subscription
    fields = ('frequency', 'service_day')
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
    
class SellerProductSellerLocationServiceInline(admin.StackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra=0

class SellerProductSellerLocationServiceRecurringFrequencyInline(admin.StackedInline):
    model = SellerProductSellerLocationServiceRecurringFrequency
    show_change_link = True
    extra=0

class SellerProductSellerLocationRentalInline(admin.StackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra=0

class SellerProductSellerLocationMaterialInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra=0

class SellerProductSellerLocationMaterialWasteTypeInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterialWasteType
    show_change_link = True
    extra=0
    
class UserGroupUserInline(admin.TabularInline):
    model = UserGroupUser
    fields = ('user_group', 'user')
    show_change_link = True
    extra=0

class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    fields = ('order_line_item_type', 'price')
    show_change_link = True
    extra=0

class OrderDisposalTicketInline(admin.TabularInline):
    model = OrderDisposalTicket
    fields = ('ticket_id', 'disposal_location', 'waste_type', 'weight')
    show_change_link = True
    extra=0


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
    list_display = ('__str__', 'main_product')
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
    search_fields = ["name",]
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
    search_fields = ["product__product_code", "seller__name"]
    list_display = ('product', 'seller')
    list_filter = ('product__main_product__main_product_category', 'seller')

class SellerProductSellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["seller_location__seller__name",]
    autocomplete_fields = ["seller_product", "seller_location"]
    list_filter = ('seller_product__product__main_product__main_product_category', 'seller_location__seller')
    inlines = [
        SellerProductSellerLocationServiceInline,
        SellerProductSellerLocationRentalInline,
        SellerProductSellerLocationMaterialInline,
    ]

class SellerProductSellerLocationServiceAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationServiceRecurringFrequencyInline,
    ]

class SellerProductSellerLocationMaterialAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationMaterialWasteTypeInline,
    ]

class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    list_display = ('name', 'user_group', 'project_id')
    autocomplete_fields = ["user_group", "user"]
    search_fields = ["name", "street"]

class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["email", "first_name", "last_name"]
    inlines = [
        UserGroupUserInline,
    ]

class UserGroupAdmin(admin.ModelAdmin):
    model = UserGroup
    search_fields = ["name"]

class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = ('user', 'user_address', 'seller_product_seller_location')
    search_fields = ["name"]
    inlines = [
        SubscriptionInline,
        OrderInline,
    ]

class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ('total_price',)
    list_display = ('order_group', 'start_date', 'end_date', 'status', 'service_date', 'total_price')
    inlines = [
        OrderLineItemInline,
        OrderDisposalTicketInline,
    ]

    def total_price(self, obj):
        order_line_items = OrderLineItem.objects.filter(order=obj)
        return sum([order_line_item.price for order_line_item in order_line_items])


class MainProductWasteTypeAdmin(admin.ModelAdmin):
    model = UserAddress
    search_fields = ["main_product__name", "waste_type__name"]

# Register your models here.
admin.site.register(Seller, SellerAdmin)
admin.site.register(SellerLocation, SellerLocationAdmin)
admin.site.register(SellerProduct, SellerProductAdmin)
admin.site.register(SellerProductSellerLocation, SellerProductSellerLocationAdmin)
admin.site.register(UserAddress, UserAddressAdmin)
admin.site.register(UserGroup, UserGroupAdmin)
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
admin.site.register(OrderGroup, OrderGroupAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLineItemType)
admin.site.register(OrderLineItem)
admin.site.register(ProductAddOnChoice)
admin.site.register(WasteType)
admin.site.register(DisposalLocation)
admin.site.register(DisposalLocationWasteType)
admin.site.register(UserSellerReview)
admin.site.register(UserAddressType)
admin.site.register(OrderDisposalTicket)
admin.site.register(ServiceRecurringFrequency)
admin.site.register(MainProductServiceRecurringFrequency)
admin.site.register(SellerProductSellerLocationService, SellerProductSellerLocationServiceAdmin)
admin.site.register(SellerProductSellerLocationServiceRecurringFrequency)
admin.site.register(SellerProductSellerLocationRental)
admin.site.register(SellerProductSellerLocationMaterial, SellerProductSellerLocationMaterialAdmin)
admin.site.register(SellerProductSellerLocationMaterialWasteType)
admin.site.register(DayOfWeek)
admin.site.register(TimeSlot)
admin.site.register(Subscription)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)

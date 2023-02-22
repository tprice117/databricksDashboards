from django.contrib import admin
from .models import *
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group


# Register your models here.
admin.site.register(Seller)
admin.site.register(UserAddress)
admin.site.register(User)
admin.site.register(AddOnChoice)
admin.site.register(AddOn)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategoryInfo)
admin.site.register(MainProductCategory)
admin.site.register(MainProductInfo)
admin.site.register(MainProduct)
admin.site.register(MainProductWasteType)
admin.site.register(OrderDetails)
admin.site.register(OrderDetailsLineItem)
admin.site.register(Order)
admin.site.register(ProductAddOnChoice)
admin.site.register(Product)
admin.site.register(SellerProduct)
admin.site.register(WasteType)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)

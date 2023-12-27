# import calendar
# import csv
# from typing import List

# import requests
# import stripe
# from django.contrib import admin, messages
# from django.contrib.auth.models import Group
# from django.contrib.auth.models import User as DjangoUser
# from django.forms import HiddenInput
# from django.shortcuts import redirect, render
# from django.urls import path
# from django.utils.html import format_html

# from api.utils.checkbook_io import CheckbookIO

# from .forms import *
# from .models import *

# stripe.api_key = settings.STRIPE_SECRET_KEY


# # Register your models here.
# admin.site.register(Seller, SellerAdmin)
# admin.site.register(SellerLocation, SellerLocationAdmin)
# admin.site.register(SellerProduct, SellerProductAdmin)
# admin.site.register(SellerProductSellerLocation, SellerProductSellerLocationAdmin)
# admin.site.register(UserAddress, UserAddressAdmin)
# admin.site.register(UserGroup, UserGroupAdmin)
# admin.site.register(User, UserAdmin)
# admin.site.register(UserGroupUser)
# admin.site.register(UserUserAddress)
# admin.site.register(AddOnChoice, AddOnChoiceAdmin)
# admin.site.register(AddOn, AddOnAdmin)
# admin.site.register(MainProductAddOn)
# admin.site.register(MainProductCategory, MainProductCategoryAdmin)
# admin.site.register(MainProductCategoryInfo)
# admin.site.register(MainProduct, MainProductAdmin)
# admin.site.register(MainProductInfo, MainProductInfoAdmin)
# admin.site.register(MainProductWasteType, MainProductWasteTypeAdmin)
# admin.site.register(Product, ProductAdmin)
# admin.site.register(OrderGroup, OrderGroupAdmin)
# admin.site.register(Order, OrderAdmin)
# admin.site.register(OrderLineItemType)
# admin.site.register(OrderLineItem)
# admin.site.register(ProductAddOnChoice)
# admin.site.register(WasteType)
# admin.site.register(DisposalLocation)
# admin.site.register(DisposalLocationWasteType)
# admin.site.register(UserSellerReview)
# admin.site.register(UserAddressType)
# admin.site.register(OrderDisposalTicket)
# admin.site.register(ServiceRecurringFrequency)
# admin.site.register(MainProductServiceRecurringFrequency)
# admin.site.register(
#     SellerProductSellerLocationService, SellerProductSellerLocationServiceAdmin
# )
# admin.site.register(SellerProductSellerLocationServiceRecurringFrequency)
# admin.site.register(SellerProductSellerLocationRental)
# admin.site.register(
#     SellerProductSellerLocationMaterial, SellerProductSellerLocationMaterialAdmin
# )
# admin.site.register(SellerProductSellerLocationMaterialWasteType)
# admin.site.register(DayOfWeek)
# admin.site.register(TimeSlot)
# admin.site.register(Subscription)
# admin.site.register(Payout, PayoutAdmin)
# admin.site.register(SellerInvoicePayable, SellerInvoicePayableAdmin)
# admin.site.register(SellerInvoicePayableLineItem, SellerInvoicePayableLineItemAdmin)

# # Unregister auth models.
# admin.site.unregister(DjangoUser)
# admin.site.unregister(Group)

from django.contrib import admin

from api.models import SellerProductSellerLocationMaterialWasteType


class SellerProductSellerLocationMaterialWasteTypeInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterialWasteType
    show_change_link = True
    extra = 0

from django.contrib import admin

from api.models import SellerProductSellerLocationMaterial


class SellerProductSellerLocationMaterialInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra = 0

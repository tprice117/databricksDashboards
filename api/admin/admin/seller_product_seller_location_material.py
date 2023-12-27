from django.contrib import admin

from api.admin.inlines import SellerProductSellerLocationMaterialWasteTypeInline
from api.models import SellerProductSellerLocationMaterial


@admin.register(SellerProductSellerLocationMaterial)
class SellerProductSellerLocationMaterialAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationMaterialWasteTypeInline,
    ]

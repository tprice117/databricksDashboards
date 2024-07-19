from django.contrib import admin

from api.models import SellerProductSellerLocationMaterialWasteType


class SellerProductSellerLocationMaterialWasteTypeInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterialWasteType
    show_change_link = True
    extra = 0
    raw_id_fields = (
        "seller_product_seller_location_material",
        "main_product_waste_type",
        "created_by",
        "updated_by",
    )

from django.contrib import admin

from api.models.order.order_group_material_waste_type import OrderGroupMaterialWasteType


class OrderGroupMaterialWasteTypeInline(admin.TabularInline):
    model = OrderGroupMaterialWasteType
    fields = [
        "main_product_waste_type",
        "price_per_ton",
        "tonnage_included",
    ]
    extra = 0

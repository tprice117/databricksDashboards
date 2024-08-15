import csv
import logging

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from api.admin.inlines.order_group_material_waste_type import (
    OrderGroupMaterialWasteTypeInline,
)
from api.forms import CsvImportForm
from api.models import SellerProductSellerLocationMaterial
from api.models.order.order_group_material import OrderGroupMaterial
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation

logger = logging.getLogger(__name__)


@admin.register(OrderGroupMaterial)
class OrderGroupMaterialAdmin(admin.ModelAdmin):
    inlines = [
        OrderGroupMaterialWasteTypeInline,
    ]

    def has_module_permission(self, request):
        return False

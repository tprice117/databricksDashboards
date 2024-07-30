from django.contrib import admin

from api.models import OrderGroupMaterial


class OrderGroupMaterialInline(admin.TabularInline):
    model = OrderGroupMaterial
    fields = ("price_per_ton", "tonnage_included")
    show_change_link = True
    extra = 0

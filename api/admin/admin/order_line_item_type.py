from django.contrib import admin

from api.models import OrderLineItemType


@admin.register(OrderLineItemType)
class OrderLineItemTypeAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
        "units",
        "code",
        "stripe_tax_code_id",
    ]

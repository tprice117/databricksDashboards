import logging
from datetime import timedelta

from django.contrib import admin
from django.utils.html import format_html

from api.models.seller.seller_product_seller_location_rental_one_step import (
    SellerProductSellerLocationRentalOneStep,
)

# from api.models.seller.seller_product_seller_location import SellerProductSellerLocation

logger = logging.getLogger(__name__)


@admin.register(SellerProductSellerLocationRentalOneStep)
class SellerProductSellerLocationRentalOneStepAdmin(admin.ModelAdmin):
    list_display = (
        "seller_product_seller_location",
        "rate",
        "updated_on",
        "created_on",
    )
    raw_id_fields = (
        "seller_product_seller_location",
        "created_by",
        "updated_by",
    )
    fields = (
        "seller_product_seller_location",
        "rate",
        "formatted_pricing_table",
        "updated_on",
    )
    readonly_fields = ("formatted_pricing_table", "updated_on")

    def formatted_pricing_table(self, obj: SellerProductSellerLocationRentalOneStep):
        """
        This function creates a string representation of a pricing table
        """
        # Prices 1 - 16 weeks
        prices = []
        if obj.rate:
            prices += [
                f"{day} {'week' if day == 1 else 'weeks'}: ${obj.get_price(duration=timedelta(days=day)):.2f}"
                for day in range(1, 112, 7)
            ]
        return format_html("<br/>".join(prices))

    formatted_pricing_table.short_description = "Price Table"

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     # NOTE: To add a dropdown filter that only shows SellerProductSellerLocations
    #     # that have a MainProduct with has_rental_one_step=True, but do not have foreign
    #     # key to a SellerProductSellerLocationRentalOneStep object.
    #     if db_field.name == "seller_product_seller_location":
    #         kwargs["queryset"] = SellerProductSellerLocation.objects.filter(
    #             seller_product__product__main_product__has_rental_one_step=True
    #         ).filter(rental_one_step__isnull=True)
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)

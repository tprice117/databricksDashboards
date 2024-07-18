import logging
from datetime import timedelta

from django.contrib import admin
from django.utils.html import format_html

from api.models.seller.seller_product_seller_location_rental_multi_step import (
    SellerProductSellerLocationRentalMultiStep,
)

logger = logging.getLogger(__name__)


@admin.register(SellerProductSellerLocationRentalMultiStep)
class SellerProductSellerLocationRentalMultiStepAdmin(admin.ModelAdmin):
    fields = (
        "hour",
        "day",
        "week",
        "two_weeks",
        "month",
        "formatted_pricing_table",
        "updated_on",
    )
    readonly_fields = ("formatted_pricing_table", "updated_on")

    def formatted_pricing_table(self, obj: SellerProductSellerLocationRentalMultiStep):
        """
        This function creates a string representation of a pricing table
        """
        # Prices for 1 to 23 hours.
        prices = [
            f"{hour} {'hour' if hour == 1 else 'hours'}: ${obj.calculate_rental_price(duration=timedelta(hours=hour)):.2f}"
            for hour in range(1, 24)
        ]

        # Prices for 1 to 30 days.
        prices += [
            f"{day} {'day' if day == 1 else 'days'}: ${obj.calculate_rental_price(duration=timedelta(days=day)):.2f}"
            for day in range(1, 31)
        ]
        return format_html("<br/>".join(prices))

    formatted_pricing_table.short_description = "Price Table"

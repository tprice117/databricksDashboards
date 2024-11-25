import logging
from datetime import timedelta

from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines.seller_product_seller_location_rental_multi_step_shift import (
    SellerProductSellerLocationRentalMultiStepShiftInline,
)
from api.models.seller.seller_product_seller_location_rental_multi_step import (
    SellerProductSellerLocationRentalMultiStep,
)
from common.admin.admin.base_admin import BaseModelAdmin

logger = logging.getLogger(__name__)


class SellerProductSellerLocationRentalMultiStepResource(resources.ModelResource):
    class Meta:
        model = SellerProductSellerLocationRentalMultiStep
        skip_unchanged = True


@admin.register(SellerProductSellerLocationRentalMultiStep)
class SellerProductSellerLocationRentalMultiStepAdmin(
    BaseModelAdmin, ExportActionMixin
):
    resource_classes = [SellerProductSellerLocationRentalMultiStepResource]
    raw_id_fields = ("seller_product_seller_location",)
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "seller_product_seller_location",
                    "hour",
                    "day",
                    "week",
                    "two_weeks",
                    "month",
                ]
            },
        ),
        (
            "Pricing Table",
            {
                "fields": [
                    "formatted_pricing_table",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]

    readonly_fields = BaseModelAdmin.readonly_fields + [
        "seller_product_seller_location",
        "formatted_pricing_table",
    ]
    inlines = [
        SellerProductSellerLocationRentalMultiStepShiftInline,
    ]

    def has_module_permission(self, request):
        return False

    def formatted_pricing_table(self, obj: SellerProductSellerLocationRentalMultiStep):
        """
        This function creates a string representation of a pricing table
        """
        # Prices for 1 to 23 hours.
        prices = [
            f"{hour} {'hour' if hour == 1 else 'hours'}: ${sum(line_item.total for line_item in obj.get_price(duration=timedelta(hours=hour), shift_count=1)):.2f}"
            for hour in range(1, 24)
        ]

        # Prices for 1 to 30 days.
        prices += [
            f"{day} {'day' if day == 1 else 'days'}: ${sum(line_item.total for line_item in obj.get_price(duration=timedelta(days=day), shift_count=1)):.2f}"
            for day in range(1, 31)
        ]
        return format_html("<br/>".join(prices))

    formatted_pricing_table.short_description = "Price Table"

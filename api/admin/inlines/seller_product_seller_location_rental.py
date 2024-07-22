from api.models import SellerProductSellerLocationRental
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "included_days",
                    "price_per_day_included",
                    "price_per_day_additional",
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

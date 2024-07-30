from api.models import SellerProductSellerLocationService
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationServiceInline(BaseModelStackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "price_per_mile",
                    "flat_rate_price",
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

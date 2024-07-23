from api.models import SellerProductSellerLocationRentalMultiStep
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalMultiStepInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRentalMultiStep
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "hour",
                    "day",
                    "week",
                    "two_weeks",
                    "month",
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

from api.models import SellerProductSellerLocationRentalMultiStepShift
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalMultiStepShiftInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRentalMultiStepShift
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "two_shift",
                    "three_shift",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields

from api.models import SellerProductSellerLocationRentalOneStep
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalOneStepInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRentalOneStep
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "rate",
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

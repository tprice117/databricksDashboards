from api.models import SellerProductSellerLocationMaterial
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationMaterialInline(BaseModelStackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

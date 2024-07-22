from api.models import SellerProductSellerLocationServiceTimesPerWeek
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationServiceTimesPerWeekInline(BaseModelStackedInline):
    model = SellerProductSellerLocationServiceTimesPerWeek
    show_change_link = True
    extra = 0
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "one_time_per_week",
                    "two_times_per_week",
                    "three_times_per_week",
                    "four_times_per_week",
                    "five_times_per_week",
                    "_is_complete",
                ]
            },
        ),
        BaseModelStackedInline.audit_fieldset,
    ]
    readonly_fields = BaseModelStackedInline.readonly_fields + ["_is_complete"]

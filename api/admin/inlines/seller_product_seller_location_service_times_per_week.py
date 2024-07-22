from api.models import SellerProductSellerLocationServiceTimesPerWeek
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationServiceTimesPerWeekInline(BaseModelStackedInline):
    model = SellerProductSellerLocationServiceTimesPerWeek
    show_change_link = True
    extra = 0
    readonly_fields = BaseModelStackedInline.readonly_fields

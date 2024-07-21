from api.models import SellerProductSellerLocationRentalOneStep
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalOneStepInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRentalOneStep
    show_change_link = True
    extra = 0
    readonly_fields = BaseModelStackedInline.readonly_fields

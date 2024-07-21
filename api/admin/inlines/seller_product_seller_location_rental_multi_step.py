from django.contrib import admin

from api.models import SellerProductSellerLocationRentalMultiStep
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalMultiStepInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRentalMultiStep
    show_change_link = True
    extra = 0
    fields = (
        "hour",
        "day",
        "week",
        "two_weeks",
        "month",
    )
    readonly_fields = BaseModelStackedInline.readonly_fields
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

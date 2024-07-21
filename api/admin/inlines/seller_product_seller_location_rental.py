from django.contrib import admin

from api.models import SellerProductSellerLocationRental
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationRentalInline(BaseModelStackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra = 0
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")
    readonly_fields = BaseModelStackedInline.readonly_fields

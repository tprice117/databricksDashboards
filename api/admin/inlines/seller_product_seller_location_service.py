from api.models import SellerProductSellerLocationService
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationServiceInline(BaseModelStackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra = 0
    readonly_fields = BaseModelStackedInline.readonly_fields
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

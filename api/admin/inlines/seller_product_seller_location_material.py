from api.models import SellerProductSellerLocationMaterial
from common.admin import BaseModelStackedInline


class SellerProductSellerLocationMaterialInline(BaseModelStackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra = 0
    readonly_fields = BaseModelStackedInline.readonly_fields
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

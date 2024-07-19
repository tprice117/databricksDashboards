from django.contrib import admin

from api.models import SellerProductSellerLocationService


class SellerProductSellerLocationServiceInline(admin.StackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra = 0
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

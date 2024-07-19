from django.contrib import admin

from api.models import SellerProductSellerLocationRental


class SellerProductSellerLocationRentalInline(admin.StackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra = 0
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

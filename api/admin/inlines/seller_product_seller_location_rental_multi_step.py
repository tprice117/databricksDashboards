from django.contrib import admin

from api.models import SellerProductSellerLocationRentalMultiStep


class SellerProductSellerLocationRentalMultiStepInline(admin.StackedInline):
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
    raw_id_fields = ("seller_product_seller_location", "created_by", "updated_by")

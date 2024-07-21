from django.contrib import admin

from api.models import SellerProductSellerLocationRentalOneStep


class SellerProductSellerLocationRentalOneStepInline(admin.StackedInline):
    model = SellerProductSellerLocationRentalOneStep
    show_change_link = True
    extra = 0

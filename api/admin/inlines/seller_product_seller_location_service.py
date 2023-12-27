from django.contrib import admin

from api.models import SellerProductSellerLocationService


class SellerProductSellerLocationServiceInline(admin.StackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra = 0

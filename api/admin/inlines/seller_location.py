from django.contrib import admin

from api.models import SellerLocation


class SellerLocationInline(admin.TabularInline):
    model = SellerLocation
    fields = ("name",)
    show_change_link = True
    extra = 0

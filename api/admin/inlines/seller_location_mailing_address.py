from django.contrib import admin

from api.models import SellerLocationMailingAddress


class SellerLocationMailingAddressInline(admin.StackedInline):
    model = SellerLocationMailingAddress
    fields = ("street", "city", "state", "postal_code", "country")
    show_change_link = True
    extra = 0

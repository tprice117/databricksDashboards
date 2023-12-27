from django.contrib import admin

from api.models import SellerProductSellerLocationServiceRecurringFrequency


class SellerProductSellerLocationServiceRecurringFrequencyInline(admin.StackedInline):
    model = SellerProductSellerLocationServiceRecurringFrequency
    show_change_link = True
    extra = 0

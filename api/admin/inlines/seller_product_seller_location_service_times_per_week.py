from django.contrib import admin

from api.models import SellerProductSellerLocationServiceTimesPerWeek


class SellerProductSellerLocationServiceTimesPerWeekInline(admin.StackedInline):
    model = SellerProductSellerLocationServiceTimesPerWeek
    show_change_link = True
    extra = 0

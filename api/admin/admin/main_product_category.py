from django.contrib import admin

from api.admin.inlines import MainProductCategoryInfoInline, MainProductInline
from api.models import MainProductCategory


@admin.register(MainProductCategory)
class MainProductCategoryAdmin(admin.ModelAdmin):
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]

from django.contrib import admin

from api.admin.inlines import MainProductCategoryInline
from api.models import MainProductCategoryGroup


@admin.register(MainProductCategoryGroup)
class MainProductCategoryGroupAdmin(admin.ModelAdmin):
    inlines = [
        MainProductCategoryInline,
    ]

from django.contrib import admin

from api.admin.inlines import AddOnChoiceInline
from api.models import AddOn


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    inlines = [
        AddOnChoiceInline,
    ]

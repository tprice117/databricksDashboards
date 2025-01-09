from django.conf import settings
from django.contrib import admin

from api.models import User
from common.admin.admin import BaseModelAdmin
from crm.models import Lead


@admin.register(Lead)
class LeadAdmin(BaseModelAdmin):
    list_display = (
        "user",
        "user_address",
        "owner",
        "status",
        "created_on",
        "created_by",
    )
    search_fields = ("id",)
    list_filter = ("status", "type", "created_on", "est_conversion_date", "owner")
    autocomplete_fields = ("user", "user_address")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "owner":
            # Only show users in the Downstream Team UserGroup.
            kwargs["queryset"] = User.customer_team_users.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

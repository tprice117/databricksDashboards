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
    list_filter = ("status", "created_on", "owner")
    raw_id_fields = ("user", "user_address")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "owner":
            # Only show users in the Downstream Team UserGroup.
            if settings.ENVIRONMENT == "TEST":
                kwargs["queryset"] = User.objects.filter(
                    user_group="bd49eaab-4b46-46c0-a9bf-bace2896b795"
                )
            else:
                # DEV: Customer Team #1 (CORE), Random Company
                kwargs["queryset"] = User.objects.filter(
                    user_group__in=[
                        "3e717df9-f811-4ddd-8d2f-a5f19b807321",
                        "38309b8e-0205-45dc-b12c-3bfa365825e2",
                    ]
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

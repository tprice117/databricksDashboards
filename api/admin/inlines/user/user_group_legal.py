from django.contrib import admin

from api.models import UserGroupLegal


class UserGroupLegalInline(admin.StackedInline):
    model = UserGroupLegal
    fields = (
        "name",
        "doing_business_as",
        "structure",
        "industry",
        "street",
        "city",
        "state",
        "postal_code",
        "country",
    )
    show_change_link = True
    extra = 0

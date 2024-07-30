from django.contrib import admin

from api.models import UserGroupBilling


class UserGroupBillingInline(admin.StackedInline):
    model = UserGroupBilling
    fields = ("email", "street", "city", "state", "postal_code", "country")
    show_change_link = True
    extra = 0

from django.contrib import admin

from external_contracts.models import ExternalContract


class ExternalContractInline(admin.TabularInline):
    model = ExternalContract
    fields = ("user_address", "supplier_name", "account_number")
    show_change_link = True
    extra = 0

from django.contrib import admin

from external_contracts.admin.inlines import ExternalContractAttachmentInline
from external_contracts.models import ExternalContract


@admin.register(ExternalContract)
class ExternalContractAdmin(admin.ModelAdmin):
    search_fields = ["user_address__name", "supplier_name", "account_number"]
    list_display = ("user_address", "supplier_name", "account_number")
    inlines = [
        ExternalContractAttachmentInline,
    ]

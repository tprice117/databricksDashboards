from django.contrib import admin

from external_contracts.models import ExternalContractAttachment


class ExternalContractAttachmentInline(admin.TabularInline):
    model = ExternalContractAttachment
    fields = ("external_contract", "file")
    show_change_link = False
    extra = 0

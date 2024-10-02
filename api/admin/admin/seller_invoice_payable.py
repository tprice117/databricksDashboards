from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin

from api.admin.filters.seller_invoice_payable.admin_tasks import (
    SellerInvoicePayableAdminTasksFilter,
)
from api.admin.inlines.seller_invoice_payable_line_item import (
    SellerInvoicePayableLineItemInline,
    LinkedOrdersSIPLI,
    InvoiceLineItem,
)
from api.models import SellerInvoicePayable
from common.admin.admin.base_admin import BaseModelAdmin


class SellerLocationFilter(AutocompleteFilter):
    title = "Seller Location"
    field_name = "seller_location"


@admin.register(SellerInvoicePayable)
class SellerInvoicePayableAdmin(BaseModelAdmin):
    model = SellerInvoicePayable
    list_display = (
        "seller_location",
        "supplier_invoice_id",
        "amount",
    )
    search_fields = [
        "id",
        "seller_location__name",
        "supplier_invoice_id",
    ]
    inlines = [
        LinkedOrdersSIPLI,
        InvoiceLineItem,
    ]
    list_filter = [
        SellerLocationFilter,
        SellerInvoicePayableAdminTasksFilter,
    ]
    fieldsets = [
        (
            "Invoice Details",
            {
                "fields": [
                    "seller_location",
                    "account_number",
                    "supplier_invoice_id",
                    "invoice_file",
                ],
            },
        ),
        (
            "Dates",
            {
                "fields": [
                    "invoice_date",
                    "due_date",
                ],
            },
        ),
        (
            "Amount",
            {
                "fields": [
                    "amount",
                ],
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
    readonly_fields = BaseModelAdmin.readonly_fields + []

from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import SellerInvoicePayableLineItem
from common.admin.admin.base_admin import BaseModelAdmin


class SellerInvoicePayableLineItemResource(resources.ModelResource):
    class Meta:
        model = SellerInvoicePayableLineItem
        skip_unchanged = True


@admin.register(SellerInvoicePayableLineItem)
class SellerInvoicePayableLineItemAdmin(BaseModelAdmin, ExportActionMixin):
    model = SellerInvoicePayableLineItem
    resource_classes = [SellerInvoicePayableLineItemResource]
    search_fields = ["id", "seller_invoice_payable__id", "order__id"]
    raw_id_fields = (
        "seller_invoice_payable",
        "order",
        "created_by",
        "updated_by",
    )
    list_display = (
        "seller_invoice_payable",
        "order",
        "amount",
        "description",
    )
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "seller_invoice_payable",
                    "order",
                    "amount",
                    "description",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]

from django.contrib import admin

import billing.models as models


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "number",
        "status",
        "amount_remaining",
        "created_on",
        "updated_on",
    )
    readonly_fields = (
        "invoice_id",
        "user_address",
        "amount_due",
        "amount_paid",
        "amount_remaining",
        "due_date",
        "hosted_invoice_url",
        "invoice_pdf",
        "metadata",
        "number",
        "paid",
        "status",
        "total",
    )

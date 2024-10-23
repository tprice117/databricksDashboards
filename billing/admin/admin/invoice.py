from django.contrib import admin

import billing.models as models


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "number",
        "status",
        "amount_due",
        "amount_paid",
        "amount_remaining",
        "total",
        "due_date",
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
    search_fields = (
        "id",
        "user_address__name",
        "user_address__street",
        "user_address__city",
        "user_address__state",
        "user_address__postal_code",
        "user_address__user_group__name",
        "invoice_id",
        "number",
    )
    raw_id_fields = ("user_address", "created_by", "updated_by")
    list_filter = ("due_date", "status")
    ordering = ("-due_date",)

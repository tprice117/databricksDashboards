from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.utils import timezone
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.filters.user_address.admin_tasks import UserAdddressAdminTasksFilter
from api.models import UserAddress
from billing.utils.billing import BillingUtils
from common.utils.stripe.stripe_utils import StripeUtils
from external_contracts.admin.inlines import ExternalContractInline
from common.admin.admin.base_admin import BaseModelAdmin


class UserAddressResource(resources.ModelResource):
    class Meta:
        model = UserAddress
        skip_unchanged = True


class UserGroupFilter(AutocompleteFilter):
    title = "User Group"
    field_name = "user_group"


@admin.register(UserAddress)
class UserAddressAdmin(BaseModelAdmin, ExportActionMixin):
    model = UserAddress
    resource_classes = [UserAddressResource]
    list_display = ("name", "user_group", "project_id")
    autocomplete_fields = ["user_group", "user"]
    readonly_fields = [
        "stripe_customer_id",
    ]
    search_fields = ["id", "name", "street"]
    list_filter = [
        UserGroupFilter,
        UserAdddressAdminTasksFilter,
    ]
    actions = [
        "create_invoices",
    ]
    inlines = [
        ExternalContractInline,
    ]
    raw_id_fields = [
        "user_group",
        "user",
        "default_payment_method",
        "created_by",
        "updated_by",
    ]

    @admin.action(
        description="Create invoices (all 'Complete' orders with end date on or before yesterday)"
    )
    def create_invoices(self, request, queryset):
        from api.models import Order
        from billing.models import Invoice

        user_address: UserAddress
        now_date = timezone.now().today()

        for user_address in queryset:
            orders = Order.objects.filter(
                status="COMPLETE",
                end_date__lte=now_date,
                order_group__user_address=user_address,
            )
            orders = [
                order for order in orders if not order.all_order_line_items_invoiced()
            ]
            invoice = BillingUtils.create_stripe_invoice_for_user_address(
                orders, user_address=user_address
            )

            # Finalize the invoice.
            StripeUtils.Invoice.finalize(invoice.id)

            # If autopay is enabled, pay the invoice.
            if user_address.user_group.autopay:
                is_paid, invoice = StripeUtils.Invoice.attempt_pay(
                    invoice.id, update_invoice_db=False
                )
            Invoice.objects.update_or_create(
                invoice_id=invoice["id"],
                defaults={
                    "user_address": UserAddress.objects.get(
                        stripe_customer_id=invoice["customer"],
                    ),
                    "amount_due": invoice["amount_due"] / 100,
                    "amount_paid": invoice["amount_paid"] / 100,
                    "amount_remaining": invoice["amount_remaining"] / 100,
                    "due_date": (
                        timezone.datetime.fromtimestamp(
                            invoice["due_date"],
                        )
                        if invoice["due_date"]
                        else None
                    ),
                    "hosted_invoice_url": invoice["hosted_invoice_url"],
                    "invoice_pdf": invoice["invoice_pdf"],
                    "metadata": invoice["metadata"],
                    "number": invoice["number"],
                    "paid": invoice["paid"],
                    "status": invoice["status"],
                    "total": invoice["total"] / 100,
                },
            )
        self.message_user(request, "Invoices created and finalized.")

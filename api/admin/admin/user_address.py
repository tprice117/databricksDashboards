from django.contrib import admin

from api.admin.filters.user_address.admin_tasks import UserAdddressAdminTasksFilter
from api.models import UserAddress
from billing.utils.billing import BillingUtils
from common.utils.stripe.stripe_utils import StripeUtils
from external_contracts.admin.inlines import ExternalContractInline


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    list_display = ("name", "user_group", "project_id")
    autocomplete_fields = ["user_group", "user"]
    readonly_fields = [
        "stripe_customer_id",
    ]
    search_fields = ["name", "street"]
    list_filter = [
        UserAdddressAdminTasksFilter,
    ]
    actions = [
        "create_invoices",
    ]
    inlines = [
        ExternalContractInline,
    ]

    @admin.action(
        description="Create invoices (all 'Complete' orders with end date on or before yesterday)"
    )
    def create_invoices(self, request, queryset):
        user_address: UserAddress
        for user_address in queryset:
            invoice = BillingUtils.create_stripe_invoice_for_user_address(
                user_address=user_address
            )

            # Finalize the invoice.
            StripeUtils.Invoice.finalize(invoice.id)

            # If autopay is enabled, pay the invoice.
            if user_address.user_group.autopay:
                StripeUtils.Invoice.attempt_pay(invoice.id)

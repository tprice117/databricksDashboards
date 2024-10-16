from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.utils import timezone

from api.admin.filters.user_address.admin_tasks import UserAdddressAdminTasksFilter
from api.models import UserAddress
from billing.utils.billing import BillingUtils
from common.utils.stripe.stripe_utils import StripeUtils
from external_contracts.admin.inlines import ExternalContractInline


class UserGroupFilter(AutocompleteFilter):
    title = "User Group"
    field_name = "user_group"


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
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

    @admin.action(
        description="Create invoices (all 'Complete' orders with end date on or before yesterday)"
    )
    def create_invoices(self, request, queryset):
        from api.models import Order

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
                StripeUtils.Invoice.attempt_pay(invoice.id)
        self.message_user(request, "Invoices created and finalized.")

import csv

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html
from django.conf import settings
from import_export.admin import ExportActionMixin
from import_export import resources

from admin_approvals.admin.inlines.user_group_admin_approval_user_invite import (
    UserGroupAdminApprovalUserInviteInline,
)
from admin_policies.admin.inlines.user_group_policy_invitation_approval import (
    UserGroupPolicyInvitationApprovalInline,
)
from admin_policies.admin.inlines.user_group_policy_monthly_limit import (
    UserGroupPolicyMonthlyLimitInline,
)
from admin_policies.admin.inlines.user_group_policy_purchase_approval import (
    UserGroupPolicyPurchaseApprovalInline,
)
from api.admin.filters import UserGroupTypeFilter
from api.admin.filters.user_group.admin_tasks import UserGroupAdminTasksFilter
from api.admin.inlines import (
    BrandingInline,
    UserGroupBillingInline,
    UserGroupCreditApplicationInline,
    UserGroupLegalInline,
    UserInline,
)
from api.forms import CsvImportForm
from api.models import UserGroup, User
from billing.utils.billing import BillingUtils
from common.admin.admin.base_admin import BaseModelAdmin


class UserGroupResource(resources.ModelResource):
    class Meta:
        model = UserGroup
        skip_unchanged = True


@admin.register(UserGroup)
class UserGroupAdmin(BaseModelAdmin, ExportActionMixin):
    model = UserGroup
    resource_classes = [UserGroupResource]
    list_display = (
        "name",
        "seller",
        "user_count",
        "seller_locations",
        "seller_product_seller_locations",
        "credit_utilization",
    )
    search_fields = ["name"]
    list_filter = (
        UserGroupTypeFilter,
        UserGroupAdminTasksFilter,
    )
    inlines = [
        BrandingInline,
        UserGroupBillingInline,
        UserGroupLegalInline,
        UserGroupCreditApplicationInline,
        UserInline,
        UserGroupPolicyMonthlyLimitInline,
        UserGroupPolicyPurchaseApprovalInline,
        UserGroupPolicyInvitationApprovalInline,
        # UserGroupAdminApprovalOrderInline, # Commented since there is not a direct relation between UserGroup and Order.
        # TODO: Find a way to add the UserGroupAdminApprovalOrderInline (non-direct foreign key) to the UserGroup.
        UserGroupAdminApprovalUserInviteInline,
    ]
    actions = [
        "create_invoices",
    ]
    raw_id_fields = ("seller", "created_by", "updated_by")

    import_export_change_list_template = "admin/entities/user_group_changelist.html"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account_owner":
            # Only show users in the Downstream Team UserGroup.
            kwargs["queryset"] = User.customer_team_users.all()
        elif db_field.name == "default_payment_method":
            from payment_methods.models import PaymentMethod

            kwargs["queryset"] = PaymentMethod.objects.filter(
                user_group=request.user.user_group
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def user_count(self, obj):
        return obj.users.count()

    def seller_locations(self, obj):
        # Get all SellerLocations for this UserGroup.
        return obj.seller.seller_locations.count() if obj.seller else None

    def seller_product_seller_locations(self, obj):
        # Get all SellerProductSellerLocations for this UserGroup.
        seller_locations = obj.seller.seller_locations.all() if obj.seller else None
        return (
            sum(
                [
                    seller_location.seller_product_seller_locations.count()
                    for seller_location in seller_locations
                ]
            )
            if seller_locations
            else None
        )

    def credit_utilization(self, obj: UserGroup):
        if obj.credit_line_limit is None:
            return "N/A"
        elif obj.credit_line_limit == 0:
            return "Denied"
        else:
            credit_used = float(obj.credit_limit_used())
            credit_line_limit = float(obj.credit_line_limit)
            if credit_used > credit_line_limit:
                return format_html(
                    f"<span style='color:red;'>Over: ${round(credit_used - credit_line_limit, 2)}</span>"
                )
            return format_html(f"{round((credit_used / credit_line_limit) * 100, 2)}%")

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if "name" not in row.keys():
                    self.message_user(
                        request,
                        "Your csv file must have a header row with 'name' as the first column.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                test, test2 = UserGroup.objects.get_or_create(
                    name=row["name"],
                )
                print(test)
                print(test2)

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

    @admin.action(
        description="Create invoices (all 'Complete' orders with end date on or before yesterday)"
    )
    def create_invoices(self, request, queryset):
        for user_group in queryset:
            print(user_group)
            BillingUtils.create_stripe_invoices_for_user_group(
                user_group=user_group,
            )

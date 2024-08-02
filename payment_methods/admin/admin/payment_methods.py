from django.contrib import admin
from django.utils import timezone
from django.db.models import Q

from payment_methods.admin.inlines import (
    PaymentMethodUserAddressInline,
    PaymentMethodUserInline,
)
from payment_methods.models import PaymentMethod
from api.models import OrderGroup


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    inlines = [
        PaymentMethodUserInline,
        PaymentMethodUserAddressInline,
    ]
    list_display = (
        "id",
        "get_user",
        "get_user_group",
        "get_active_orders",
        "active",
    )
    list_filter = ("active",)
    search_fields = ["user__email", "user_group__name", "id", "token"]

    @admin.display(ordering="user__email", description="User Email")
    def get_user(self, obj):
        return obj.user.email

    @admin.display(ordering="user_group__name", description="User Group Name")
    def get_user_group(self, obj):
        return obj.user_group.name

    @admin.display(description="Active Orders")
    def get_active_orders(self, obj):
        today = timezone.datetime.today()
        # Active orders are those that have an end_date in the future or are null (recurring orders).
        order_groups = OrderGroup.objects.filter(user_id=obj.user_id).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        )
        return order_groups.count()

    def get_readonly_fields(self, request, obj=None):
        # If PaymentMethod is being edited,
        # show card fields (read-only).
        if obj:
            return self.readonly_fields + (
                "token",
                "card_number",
                "card_brand",
                "card_exp_month",
                "card_exp_year",
            )
        else:
            # If PaymentMethod is being added, don't show card fields.
            return self.readonly_fields

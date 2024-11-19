from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import Payout
from common.admin.admin.base_admin import BaseModelAdmin


class PayoutResource(resources.ModelResource):
    class Meta:
        model = Payout
        skip_unchanged = True


@admin.register(Payout)
class PayoutAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [PayoutResource]
    model = Payout
    list_display = (
        "id",
        "order",
        "checkbook_payout_id",
        "check_number",
        "stripe_transfer_id",
        "lob_check_id",
        "amount",
        "created_on",
    )
    search_fields = ["id", "lob_check_id", "checkbook_payout_id", "stripe_transfer_id"]
    raw_id_fields = ("order", "created_by", "updated_by")
    list_filter = ("created_on",)
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "order",
                    "checkbook_payout_id",
                    "check_number",
                    "stripe_transfer_id",
                    "lob_check_id",
                    "amount",
                    "description",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]

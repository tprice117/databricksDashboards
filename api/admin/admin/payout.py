from django.contrib import admin

from api.models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
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

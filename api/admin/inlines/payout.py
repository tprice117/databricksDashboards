from django.contrib import admin

from api.models import Payout


class PayoutInline(admin.TabularInline):
    model = Payout
    fields = (
        "amount",
        "description",
        "stripe_transfer_id",
        "check_number",
        "lob_check_id",
    )
    show_change_link = True
    extra = 0
    can_delete = False

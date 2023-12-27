from django.contrib import admin

from api.models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    model = Payout
    search_fields = ["id", "melio_payout_id", "stripe_transfer_id"]

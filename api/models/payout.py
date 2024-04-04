from django.db import models

from common.models import BaseModel


class Payout(BaseModel):
    order = models.ForeignKey("api.Order", models.CASCADE, related_name="payouts")
    checkbook_payout_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    lob_check_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

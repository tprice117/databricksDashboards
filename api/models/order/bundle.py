from django.db import models
from common.models import BaseModel
from api.models.user.user_address import UserAddress


class Bundle(BaseModel):
    # user_address = models.ForeignKey(
    #     UserAddress,
    #     models.PROTECT,
    #     related_name="bundles",
    # )
    name = models.CharField(max_length=255, blank=True, null=True)
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )

    # class Meta:
    #     verbose_name = "Bundle"
    #     verbose_name_plural = "Bundles"

    def __str__(self):
        return f"{self.name or 'bundle'}"

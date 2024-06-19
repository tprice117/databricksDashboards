from django.core.exceptions import ValidationError
from django.db import models

from asset_management.models import Asset
from common.models import BaseModel


class AssetHours(BaseModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="hours",
    )
    hours = models.IntegerField()

    class Meta:
        verbose_name = "Asset Hours"
        verbose_name_plural = "Asset Hours"

    def clean(self):
        super().clean()

        # Ensure the hours are equal to or greater than any other hours for this asset.
        if self.pk:
            asset_hours = AssetHours.objects.filter(asset=self.asset).exclude(
                pk=self.pk
            )
        else:
            asset_hours = AssetHours.objects.filter(asset=self.asset)

        if asset_hours.exists():
            max_hours = asset_hours.aggregate(models.Max("hours"))["hours__max"]
            if self.hours < max_hours:
                raise ValidationError(
                    "Hours must be equal to or greater than any other hours for this asset."
                )

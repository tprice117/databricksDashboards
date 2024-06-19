from django.db import models

from asset_management.models import Asset
from common.models import BaseModel


class AssetReplacementValue(BaseModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
    )
    replacement_value = models.IntegerField()

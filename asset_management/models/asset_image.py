from django.db import models

from asset_management.models import Asset
from common.models import BaseModel
from common.utils.get_file_path import get_file_path


class AssetImage(BaseModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to=get_file_path)

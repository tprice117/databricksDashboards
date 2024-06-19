from django.db import models
from django.utils.html import format_html

from asset_management.models import Asset
from common.models import BaseModel
from common.utils.get_file_path import get_file_path


class AssetImage(BaseModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to=get_file_path)

    @property
    def image_tag(self: "AssetImage"):
        return format_html(
            '<img src="{}" style="max-width:200px; max-height:200px"/>'.format(
                self.image.url
            )
        )

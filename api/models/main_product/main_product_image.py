from django.db import models

from api.models.main_product.main_product import MainProduct
from common.models import BaseModel
from common.utils.get_file_path import get_file_path


class MainProductImage(BaseModel):
    """Model storing multiple images of a main product to be displayed in a carousel."""

    main_product = models.ForeignKey(
        MainProduct,
        models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=get_file_path)
    sort = models.IntegerField(default=0)

    def __str__(self):
        return self.image.name

    class Meta:
        ordering = ["sort"]

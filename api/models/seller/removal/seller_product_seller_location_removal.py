from django.db import models

from common.models import BaseModel


class SellerProductSellerLocationRemoval(BaseModel):
    """
    NOT CURRENTLY IN USE. CONCEPT FOR FUTURE-USE ONLY.
    """

    """
    This model is used to store the removal information for a seller product seller location.
    If this model exists, then the SellerProductSellerLocation charges a removal fee. The price
    of the removal is determined either the SellerProductSellerLocationRemovalFlatRate or the
    SellerProductSellerLocationRemovalPerMile model.
    """

    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="removal",
    )

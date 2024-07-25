from django.db import models

from common.models import BaseModel


class SellerProductSellerLocationDelivery(BaseModel):
    """
    NOT CURRENTLY IN USE. CONCEPT FOR FUTURE-USE ONLY.
    """

    """
    This model is used to store the delivery information for a seller product seller location.
    If this model exists, then the SellerProductSellerLocation charges a delivery fee. The price
    of the delivery is determined either the SellerProductSellerLocationDeliveryFlatRate or the
    SellerProductSellerLocationDeliveryPerMile model.
    """

    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="delivery",
    )

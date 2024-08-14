from django.db import models

from api.models.common.rental_multi_step import RentalMultiStep


class SellerProductSellerLocationRentalMultiStep(RentalMultiStep):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental_multi_step",
    )

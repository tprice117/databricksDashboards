from django.db import models

from api.models.common.rental_one_step import PricingRentalOneStep


class SellerProductSellerLocationRentalOneStep(PricingRentalOneStep):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental_one_step",
    )

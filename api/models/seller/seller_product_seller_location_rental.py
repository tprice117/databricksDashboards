from django.db import models

from api.models.common.rental_two_step import PricingRentalTwoStep


class SellerProductSellerLocationRental(PricingRentalTwoStep):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental",
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

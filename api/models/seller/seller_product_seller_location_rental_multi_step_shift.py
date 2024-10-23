from django.db import models

from api.models.common.rental_multi_step_shift import PricingRentalMultiStepShift
from api.models.seller.seller_product_seller_location_rental_multi_step import (
    SellerProductSellerLocationRentalMultiStep,
)


class SellerProductSellerLocationRentalMultiStepShift(PricingRentalMultiStepShift):
    seller_product_seller_location_multi_step = models.OneToOneField(
        SellerProductSellerLocationRentalMultiStep,
        on_delete=models.CASCADE,
        related_name="rental_multi_step_shift",
    )

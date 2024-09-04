from django.db import models

from api.models.common.rental_multi_step_shift import PricingRentalMultiStepShift
from api.models.order.order_group_rental_multi_step import OrderGroupRentalMultiStep


class OrderGroupRentalMultiStepShift(PricingRentalMultiStepShift):
    order_group_rental_multi_step = models.OneToOneField(
        OrderGroupRentalMultiStep,
        on_delete=models.CASCADE,
        related_name="rental_multi_step_shift",
    )

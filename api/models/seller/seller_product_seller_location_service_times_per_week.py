from django.db import models

from api.models.common.services_times_per_week import PricingServiceTimesPerWeek


class SellerProductSellerLocationServiceTimesPerWeek(PricingServiceTimesPerWeek):
    """
    This model represents the service times per week for a seller product seller location.
    Currently, it is specifically designed for Portable Toilet service pricing. Each price
    field represents the price for a specific number of times per week, quoted as a monthly rate.

    For example, if the one_time_per_week field is set to 100, then a customer will be charged
    100 for a portable toilet service that is serviced once per week for up to a month.
    """

    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="service_times_per_week",
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

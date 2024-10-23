from django.db import models
from django.db.models.signals import post_save

from api.models.common.service import PricingService
from api.models.main_product.main_product_service_recurring_frequency import (
    MainProductServiceRecurringFrequency,
)
from api.models.seller.seller_product_seller_location_service_recurring_frequency import (
    SellerProductSellerLocationServiceRecurringFrequency,
)


class SellerProductSellerLocationService(PricingService):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="service",
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

    def post_save(sender, instance, created, **kwargs):
        # Ensure all service recurring frequencies are created.
        for (
            service_recurring_frequency
        ) in MainProductServiceRecurringFrequency.objects.filter(
            main_product=instance.seller_product_seller_location.seller_product.product.main_product
        ):
            if not SellerProductSellerLocationServiceRecurringFrequency.objects.filter(
                seller_product_seller_location_service=instance,
                main_product_service_recurring_frequency=service_recurring_frequency,
            ).exists():
                SellerProductSellerLocationServiceRecurringFrequency.objects.create(
                    seller_product_seller_location_service=instance,
                    main_product_service_recurring_frequency=service_recurring_frequency,
                )

        # Ensure all "stale" service recurring frequencies are deleted.
        for (
            seller_product_seller_location_service_recurring_frequency
        ) in SellerProductSellerLocationServiceRecurringFrequency.objects.filter(
            seller_product_seller_location_service=instance
        ):
            if not MainProductServiceRecurringFrequency.objects.filter(
                main_product=seller_product_seller_location_service_recurring_frequency.main_product_service_recurring_frequency.main_product,
                service_recurring_frequency=seller_product_seller_location_service_recurring_frequency.main_product_service_recurring_frequency.service_recurring_frequency,
            ).exists():
                seller_product_seller_location_service_recurring_frequency.delete()


post_save.connect(
    SellerProductSellerLocationService.post_save,
    sender=SellerProductSellerLocationService,
)

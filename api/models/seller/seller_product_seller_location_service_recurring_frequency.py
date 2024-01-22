from django.db import models

from api.models.main_product.main_product_service_recurring_frequency import (
    MainProductServiceRecurringFrequency,
)
from common.models import BaseModel


class SellerProductSellerLocationServiceRecurringFrequency(BaseModel):
    seller_product_seller_location_service = models.ForeignKey(
        "api.SellerProductSellerLocationService", models.PROTECT
    )
    main_product_service_recurring_frequency = models.ForeignKey(
        MainProductServiceRecurringFrequency,
        models.PROTECT,
    )
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = (
            "seller_product_seller_location_service",
            "main_product_service_recurring_frequency",
        )

    def __str__(self):
        return f"{self.seller_product_seller_location_service.seller_product_seller_location.seller_location.name} - {self.main_product_service_recurring_frequency.main_product.name}"

from django.db import models
from django.db.models.signals import post_save

from api.models.seller.seller_location import SellerLocation
from api.models.seller.seller_product import SellerProduct
from api.models.seller.seller_product_seller_location_material import (
    SellerProductSellerLocationMaterial,
)
from api.models.seller.seller_product_seller_location_material_waste_type import (
    SellerProductSellerLocationMaterialWasteType,
)
from api.models.seller.seller_product_seller_location_rental import (
    SellerProductSellerLocationRental,
)
from api.models.seller.seller_product_seller_location_service import (
    SellerProductSellerLocationService,
)
from api.pricing_ml.pricing import Price_Model
from common.models import BaseModel


class SellerProductSellerLocation(BaseModel):
    seller_product = models.ForeignKey(
        SellerProduct, models.CASCADE, related_name="seller_product_seller_locations"
    )
    seller_location = models.ForeignKey(
        SellerLocation, models.CASCADE, related_name="seller_product_seller_locations"
    )
    active = models.BooleanField(default=True)
    total_inventory = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )  # Added 2/20/2023 Total Quantity input by seller of product offered
    min_price = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    max_price = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    service_radius = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    fuel_environmental_markup = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )

    class Meta:
        unique_together = (
            "seller_product",
            "seller_location",
        )

    @property
    def price_from(self):
        # Get lowest price WasteType for this SellerProductSellerLocation.
        seller_product_seller_location_waste_type = (
            SellerProductSellerLocationMaterialWasteType.objects.filter(
                seller_product_seller_location_material__seller_product_seller_location=self
            )
            .order_by("price_per_ton")
            .first()
        )

        # Get pricing information for the lowest price configuration.
        pricing = Price_Model.get_price_for_seller_product_seller_location(
            seller_product_seller_location=self,
            customer_latitude=self.seller_location.latitude,
            customer_longitude=self.seller_location.longitude,
            waste_type=(
                seller_product_seller_location_waste_type.main_product_waste_type.waste_type
                if seller_product_seller_location_waste_type
                else None
            ),
        )

        # Compute the price.
        service = (
            pricing["service"]["rate"]
            if "service" in pricing
            and pricing["service"]
            and pricing["service"]["is_flat_rate"]
            else 0
        )
        rental = (
            pricing["rental"]["included_days"]
            * pricing["rental"]["price_per_day_included"]
            if "rental" in pricing
            and pricing["rental"]
            and "price_per_day_included" in pricing["rental"]
            and "included_days" in pricing["rental"]
            else 0
        )
        material = (
            pricing["material"]["price_per_ton"]
            * pricing["material"]["tonnage_included"]
            if "material" in pricing
            and pricing["material"]
            and "price_per_ton" in pricing["material"]
            and "tonnage_included" in pricing["material"]
            else 0
        )

        return service + rental + material

    def __str__(self):
        return f'{self.seller_location.name if self.seller_location and self.seller_location.name else ""} - {self.seller_product.product.main_product.name if self.seller_product and self.seller_product.product and self.seller_product.product.main_product and self.seller_product.product.main_product.name else ""}'

    def is_complete(self):
        # Rental.
        rental_one_step_complete = (
            hasattr(self, "rental_one_step") and self.rental_one_step.is_complete()
            if self.seller_product.product.main_product.has_rental_one_step
            else True
        )
        rental_two_step_complete = (
            hasattr(self, "rental") and self.rental.is_complete()
            if self.seller_product.product.main_product.has_rental
            else True
        )
        rental_multi_step_complete = (
            hasattr(self, "rental_multi_step") and self.rental_multi_step.is_complete()
            if self.seller_product.product.main_product.has_rental_multi_step
            else True
        )

        # Service.
        service_times_per_week_complete = (
            hasattr(self, "service_times_per_week")
            and self.service_times_per_week.is_complete()
            if self.seller_product.product.main_product.has_service_times_per_week
            else True
        )

        # Material.
        material_is_complete = (
            hasattr(self, "material") and self.material.is_complete()
            if self.seller_product.product.main_product.has_material
            else True
        )

        return (
            rental_one_step_complete
            and rental_two_step_complete
            and rental_multi_step_complete
            and service_times_per_week_complete
            and material_is_complete
        )

    def post_save(sender, instance, created, **kwargs):
        # Create/delete Service.
        if (
            not hasattr(instance, "service")
            and instance.seller_product.product.main_product.has_service
        ):
            SellerProductSellerLocationService.objects.create(
                seller_product_seller_location=instance
            )
        elif (
            hasattr(instance, "service")
            and not instance.seller_product.product.main_product.has_service
        ):
            instance.service.delete()

        # Create/delete Rental.
        if (
            not hasattr(instance, "rental")
            and instance.seller_product.product.main_product.has_rental
        ):
            SellerProductSellerLocationRental.objects.create(
                seller_product_seller_location=instance
            )
        elif (
            hasattr(instance, "rental")
            and not instance.seller_product.product.main_product.has_rental
        ):
            instance.rental.delete()

        # Create/delete Material.
        if (
            not hasattr(instance, "material")
            and instance.seller_product.product.main_product.has_material
        ):
            SellerProductSellerLocationMaterial.objects.create(
                seller_product_seller_location=instance
            )
        elif (
            hasattr(instance, "material")
            and not instance.seller_product.product.main_product.has_material
        ):
            instance.material.delete()


post_save.connect(
    SellerProductSellerLocation.post_save, sender=SellerProductSellerLocation
)

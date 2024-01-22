from django.db import models
from django.db.models.signals import post_save

from api.models.seller.seller_location import SellerLocation
from api.models.seller.seller_product import SellerProduct
from api.models.seller.seller_product_seller_location_material import (
    SellerProductSellerLocationMaterial,
)
from api.models.seller.seller_product_seller_location_rental import (
    SellerProductSellerLocationRental,
)
from api.models.seller.seller_product_seller_location_service import (
    SellerProductSellerLocationService,
)
from common.models import BaseModel


class SellerProductSellerLocation(BaseModel):
    seller_product = models.ForeignKey(
        SellerProduct, models.CASCADE, related_name="seller_location_seller_products"
    )
    seller_location = models.ForeignKey(
        SellerLocation, models.CASCADE, related_name="seller_location_seller_products"
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

    def __str__(self):
        return f'{self.seller_location.name if self.seller_location and self.seller_location.name else ""} - {self.seller_product.product.main_product.name if self.seller_product and self.seller_product.product and self.seller_product.product.main_product and self.seller_product.product.main_product.name else ""}'

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

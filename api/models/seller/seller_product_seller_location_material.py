from django.db import models
from django.db.models.signals import post_save

from api.models.main_product.main_product_waste_type import MainProductWasteType
from api.models.seller.seller_product_seller_location_material_waste_type import (
    SellerProductSellerLocationMaterialWasteType,
)
from common.models import BaseModel


class SellerProductSellerLocationMaterial(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="material",
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

    def post_save(sender, instance, created, **kwargs):
        # Ensure all material waste type recurring frequencies are created. Only execute on create.
        if created:
            for main_product_waste_type in MainProductWasteType.objects.filter(
                main_product=instance.seller_product_seller_location.seller_product.product.main_product
            ):
                if not SellerProductSellerLocationMaterialWasteType.objects.filter(
                    seller_product_seller_location_material=instance.seller_product_seller_location.material,
                    main_product_waste_type=main_product_waste_type,
                ).exists():
                    SellerProductSellerLocationMaterialWasteType.objects.create(
                        seller_product_seller_location_material=instance.seller_product_seller_location.material,
                        main_product_waste_type=main_product_waste_type,
                    )

        # Ensure all "stale" material waste type recurring frequencies are deleted.
        for (
            seller_product_seller_location_material_waste_type
        ) in SellerProductSellerLocationMaterialWasteType.objects.filter(
            seller_product_seller_location_material=instance
        ):
            if not MainProductWasteType.objects.filter(
                main_product=instance.seller_product_seller_location.seller_product.product.main_product,
                waste_type=seller_product_seller_location_material_waste_type.main_product_waste_type.waste_type,
            ).exists():
                seller_product_seller_location_material_waste_type.delete()


post_save.connect(
    SellerProductSellerLocationMaterial.post_save,
    sender=SellerProductSellerLocationMaterial,
)

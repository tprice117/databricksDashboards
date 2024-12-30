from django.db import models
from django.db.models import Q, Case, When, Sum, Max
from django.db.models.signals import post_save
from django.utils import timezone

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
from common.models import BaseModel

PRICING_ENGINE = None
PRICING_ENGINE_RESPONSE_SERIALIZER = None


def get_pricing_engine():
    """This function returns the PricingEngine object. If the PricingEngine object does not exist, it creates a new one.
    This just makes so PricingEngine is not reinstatiated every time it is called.
    This also avoid the circular import issue."""
    global PRICING_ENGINE
    if PRICING_ENGINE is None:
        from pricing_engine.pricing_engine import PricingEngine

        PRICING_ENGINE = PricingEngine()
    return PRICING_ENGINE


def get_pricing_engine_response_serializer(pricing):
    """This function returns the PricingEngineResponseSerializer object. If the PricingEngineResponseSerializer object does not exist, it creates a new one.
    This just makes so PricingEngineResponseSerializer is not reinstatiated every time it is called.
    This also avoid the circular import issue."""
    global PRICING_ENGINE_RESPONSE_SERIALIZER
    if PRICING_ENGINE_RESPONSE_SERIALIZER is None:
        from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
            PricingEngineResponseSerializer,
        )

        PRICING_ENGINE_RESPONSE_SERIALIZER = PricingEngineResponseSerializer(pricing)
    return PRICING_ENGINE_RESPONSE_SERIALIZER


class SellerProductSellerLocationQuerySet(models.QuerySet):
    def with_last_checkout(self):
        """Annotate the queryset with the most recent checkout date."""
        return self.annotate(
            last_checkout=Max(
                "order_groups__orders__submitted_on",
            ),
        )

    def with_ratings(self):
        """Annotate the queryset with the total number of thumbs up ratings."""
        return self.annotate(
            rating=Sum(
                Case(
                    When(
                        order_groups__orders__review__rating=True,
                        then=1,
                    ),
                    default=0,
                )
            )
        )

    def _get_complete_condition(self):
        rental_one_step_complete = Q(
            seller_product__product__main_product__has_rental_one_step=False
        ) | Q(rental_one_step__rate__gt=0)

        rental_two_step_complete = Q(
            seller_product__product__main_product__has_rental=False
        ) | Q(
            rental__price_per_day_included__gt=0,
            rental__price_per_day_additional__gt=0,
        )

        rental_multi_step_complete = (
            Q(seller_product__product__main_product__has_rental_multi_step=False)
            | Q(rental_multi_step__hour__isnull=False)
            | Q(rental_multi_step__day__isnull=False)
            | Q(rental_multi_step__week__isnull=False)
            | Q(rental_multi_step__two_weeks__isnull=False)
            | Q(rental_multi_step__month__isnull=False)
        )

        service_complete = (
            Q(seller_product__product__main_product__has_service=False)
            | Q(service__price_per_mile__gt=0)
            | Q(service__flat_rate_price__gt=0)
        )

        service_times_per_week_complete = (
            Q(seller_product__product__main_product__has_service_times_per_week=False)
            | Q(service_times_per_week__one_time_per_week__isnull=False)
            | Q(service_times_per_week__two_times_per_week__isnull=False)
            | Q(service_times_per_week__three_times_per_week__isnull=False)
            | Q(service_times_per_week__four_times_per_week__isnull=False)
            | Q(service_times_per_week__five_times_per_week__isnull=False)
        )

        material_is_complete = Q(
            seller_product__product__main_product__has_material=False
        ) | Q(material__waste_types__isnull=False)

        # Combine all conditions
        complete_condition = (
            rental_one_step_complete
            & rental_two_step_complete
            & rental_multi_step_complete
            & service_complete
            & service_times_per_week_complete
            & material_is_complete
        )

        return complete_condition

    def get_active(self):
        complete_condition = self._get_complete_condition()
        # Get all objects that fulfill the condition
        return self.filter(complete_condition, active=True).distinct()

    def get_needs_attention(self):
        complete_condition = self._get_complete_condition()
        # Get all objects where active=True but complete_condition is false
        return self.filter(active=True).exclude(complete_condition).distinct()

    def get_inactive(self):
        return self.filter(active=False).distinct()


class SellerProductSellerLocationManager(models.Manager):
    def get_queryset(self):
        return SellerProductSellerLocationQuerySet(self.model, using=self._db)

    def with_last_checkout(self):
        return self.get_queryset().with_last_checkout()

    def with_ratings(self):
        return self.get_queryset().with_ratings()

    def get_active(self):
        return self.get_queryset().get_active()

    def get_needs_attention(self):
        return self.get_queryset().get_needs_attention()

    def get_inactive(self):
        return self.get_queryset().get_inactive()


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
    # Service radius in miles
    service_radius = models.DecimalField(max_digits=18, decimal_places=0, default=40)
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    fuel_environmental_markup = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Percentage (ex: 35 means 35%)",
    )

    # Manager for chaining custom queries.
    objects = SellerProductSellerLocationManager()

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
        pricing = get_pricing_engine().get_price_by_lat_long(
            latitude=self.seller_location.latitude,
            longitude=self.seller_location.longitude,
            seller_product_seller_location=self,
            start_date=timezone.now(),
            end_date=timezone.now(),
            waste_type=(
                seller_product_seller_location_waste_type.main_product_waste_type.waste_type
                if seller_product_seller_location_waste_type
                else None
            ),
            times_per_week=(
                1
                if self.seller_product.product.main_product.has_service_times_per_week
                else None
            ),
        )

        # Return the total price.
        data = get_pricing_engine_response_serializer(pricing).data
        if "total" not in data:
            return None
        return data["total"] if pricing else None

    def __str__(self):
        return f'{self.seller_location.name if self.seller_location and self.seller_location.name else ""} - {self.seller_product.product.main_product.name if self.seller_product and self.seller_product.product and self.seller_product.product.main_product and self.seller_product.product.main_product.name else ""}'

    def _is_complete(self):
        # Rental.
        rental_one_step_complete = (
            hasattr(self, "rental_one_step") and self.rental_one_step.is_complete
            if self.seller_product.product.main_product.has_rental_one_step
            else True
        )
        rental_two_step_complete = (
            hasattr(self, "rental") and self.rental.is_complete
            if self.seller_product.product.main_product.has_rental
            else True
        )
        rental_multi_step_complete = (
            hasattr(self, "rental_multi_step") and self.rental_multi_step.is_complete
            if self.seller_product.product.main_product.has_rental_multi_step
            else True
        )

        # Service.
        service_complete = (
            hasattr(self, "service") and self.service.is_complete
            if self.seller_product.product.main_product.has_service
            else True
        )

        service_times_per_week_complete = (
            hasattr(self, "service_times_per_week")
            and self.service_times_per_week.is_complete
            if self.seller_product.product.main_product.has_service_times_per_week
            else True
        )

        # Material.
        material_is_complete = (
            hasattr(self, "material") and self.material.is_complete
            if self.seller_product.product.main_product.has_material
            else True
        )

        return (
            rental_one_step_complete
            and rental_two_step_complete
            and rental_multi_step_complete
            and service_complete
            and service_times_per_week_complete
            and material_is_complete
        )

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    # The following code is not up to date with the current pricing structure.
    # Furthermore it is bypassed by bulk_create in the BaseProductLocationFormSet
    # Therefore it is commented out for now.

    # def post_save(sender, instance, created, **kwargs):
    # Create/delete Service.
    # if (
    #     not hasattr(instance, "service")
    #     and instance.seller_product.product.main_product.has_service
    # ):
    #     SellerProductSellerLocationService.objects.create(
    #         seller_product_seller_location=instance
    #     )
    # elif (
    #     hasattr(instance, "service")
    #     and not instance.seller_product.product.main_product.has_service
    # ):
    #     instance.service.delete()

    # # Create/delete Rental.
    # if (
    #     not hasattr(instance, "rental")
    #     and instance.seller_product.product.main_product.has_rental
    # ):
    #     SellerProductSellerLocationRental.objects.create(
    #         seller_product_seller_location=instance
    #     )
    # elif (
    #     hasattr(instance, "rental")
    #     and not instance.seller_product.product.main_product.has_rental
    # ):
    #     instance.rental.delete()

    # # Create/delete Material.
    # if (
    #     not hasattr(instance, "material")
    #     and instance.seller_product.product.main_product.has_material
    # ):
    #     SellerProductSellerLocationMaterial.objects.create(
    #         seller_product_seller_location=instance
    #     )
    # elif (
    #     hasattr(instance, "material")
    #     and not instance.seller_product.product.main_product.has_material
    # ):
    #     instance.material.delete()


# post_save.connect(
#     SellerProductSellerLocation.post_save, sender=SellerProductSellerLocation
# )

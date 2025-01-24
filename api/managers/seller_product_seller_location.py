from django.db import models
from django.db.models import Q, Count, Max


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
            rating=Count(
                "order_groups__orders__review",
                filter=Q(
                    order_groups__orders__review__rating=True,
                ),
                distinct=True,
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

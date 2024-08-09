from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.main_product.main_product_category import MainProductCategory
from api.models.main_product.main_product_tag import MainProductTag
from common.models import BaseModel


class MainProduct(BaseModel):
    main_product_category = models.ForeignKey(
        MainProductCategory,
        models.CASCADE,
        related_name="main_products",
    )
    name = models.CharField(max_length=80)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    sort = models.IntegerField()
    tags = models.ManyToManyField(
        MainProductTag,
        related_name="tags",
        blank=True,
    )

    # Mark Up Configuration.
    default_take_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=20,
        help_text="Default mark up for this product (ex: 35 means 35%)",
    )
    minimum_take_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=20,
        help_text="Minimum take rate for this product (ex: 10 means 10%)",
    )

    included_tonnage_quantity = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    max_tonnage_quantity = models.DecimalField(
        max_digits=18, decimal_places=0, blank=True, null=True
    )
    main_product_code = models.CharField(max_length=255, blank=True, null=True)

    # Pricing Model Configuration.
    # 'has_rental` is the legacy pricing model. It should be
    # changed to 'RentalTwoStep' at some point.
    has_rental = models.BooleanField(default=False)
    has_rental_one_step = models.BooleanField(default=False)
    has_rental_multi_step = models.BooleanField(default=False)
    has_service = models.BooleanField(default=False)
    has_service_times_per_week = models.BooleanField(default=False)
    has_material = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.main_product_category.name} - {self.name}"

    @property
    def max_discount(self):
        """Returns the maximum discount for this MainProduct as a decimal (0 < x < 1)."""
        return 1 - ((1 + self.minimum_take_rate) / (1 + self.default_take_rate))

    @property
    def price_from(self):
        # Get all SellerProductSellerLocations for this MainProduct
        seller_product_seller_locations = []
        for product in self.products.all():
            for seller_product in product.seller_products.all():
                for (
                    seller_product_seller_location
                ) in seller_product.seller_product_seller_locations.all():
                    seller_product_seller_locations.append(
                        seller_product_seller_location
                    )

        # Get the lowest price from all SellerProductSellerLocations.
        price = None
        for seller_product_seller_location in seller_product_seller_locations:
            price_from = seller_product_seller_location.price_from
            if price is None or price_from < price:
                price = price_from

        return price

    def _is_complete(self) -> bool:
        # Given all related AddOns, ensure that we have a Product
        # for each combination of MainProduct AddOnsChoices.
        # For example, say we have AddOns A, B, and C. A has 2
        # choices,mB has 3 choices, and C has 2 choices. We should
        # have 2 * 3 * 2 = 12 Products.
        add_ons = self.add_ons.all()
        num_choices = [len(add_on.choices.all()) for add_on in add_ons]
        num_products = 1
        for choice in num_choices:
            num_products *= choice

        return num_products == self.products.count()

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)


@receiver(pre_save, sender=MainProduct)
def pre_save_main_product(sender, instance: MainProduct, **kwargs):
    # Ensure that if [has_material] is True, [included_tonnage_quantity] is not None.
    if instance.has_material and instance.included_tonnage_quantity is None:
        raise ValueError(
            "MainProduct must have included tonnage quantity since [has_material] is True."
        )

from django.core.exceptions import ValidationError
from django.db import models

from api.models.main_product.main_product_category_group import MainProductCategoryGroup
from common.models import BaseModel
from common.utils.get_file_path import get_file_path


class MainProductCategory(BaseModel):
    def validate_file_extension(value):
        allowed_extensions = [".svg", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]
        if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
                f"Only image files with extensions {', '.join(allowed_extensions)} are allowed."
            )

    group = models.ForeignKey(
        MainProductCategoryGroup,
        on_delete=models.CASCADE,
        related_name="main_product_categories",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.FileField(
        upload_to=get_file_path,
        blank=True,
        null=True,
        validators=[
            validate_file_extension,
        ],
    )
    sort = models.IntegerField()
    main_product_category_code = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"

    @property
    def price_from(self):
        # Get all MainProducts for this MainProductCategory.
        main_products = self.main_products.all()

        # Get the lowest price from all MainProducts.
        price = None
        for main_product in main_products:
            price_from = main_product.price_from
            if (price is None and price_from is not None and price_from != 0) or (
                price_from is not None and price_from != 0 and price_from < price
            ):
                price = price_from

        return price

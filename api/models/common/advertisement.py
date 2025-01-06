from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.main_product.main_product_category import MainProductCategory
from common.models import BaseModel
from common.utils.get_file_path import get_file_path
from django.core.exceptions import ValidationError


class AdvertisementObjectType(models.TextChoices):
    """Choices for the type of object that an advertisement can link to."""

    # 1. Add more choices here as needed. (Ex: Seller, MainProduct, etc.)
    MAIN_PRODUCT_CATEGORY = "main_product_category", _("Product Category")


class Advertisement(BaseModel):
    """Model for an Advertisement to be displayed on home page carousel."""

    text = models.TextField(
        max_length=50,
        help_text="Short text segment that will be displayed on the advertisement.",
    )
    image = models.ImageField(upload_to=get_file_path)
    is_active = models.BooleanField(default=True)
    sort = models.IntegerField(default=0)

    # Colors
    background_color = models.CharField(max_length=7, help_text="Hex color code.")
    text_color = models.CharField(
        max_length=7, help_text="Hex color code.", default="#000000"
    )

    # Foreign Keys
    object_type = models.CharField(
        choices=AdvertisementObjectType.choices,
        default=AdvertisementObjectType.MAIN_PRODUCT_CATEGORY,
    )

    # 2. Add nullable keys here corresponding to the object types in AdvertisementObjectType
    # Ex: Seller, MainProduct, etc.
    # The keys should be mutually exclusive
    # Reference: https://lukeplant.me.uk/blog/posts/avoid-django-genericforeignkey/#alternative-1-nullable-fields-on-source-table
    main_product_category = models.ForeignKey(
        MainProductCategory, on_delete=models.CASCADE, null=True, blank=True
    )

    # Optional Fields
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    @property
    def linked_object(self):
        """Return the object that will be linked to the advertisement. Raises an error if no object is set."""
        if self.main_product_category is not None:
            return self.main_product_category
        # 3. Repeat for each object type
        raise AssertionError("No linked object found.")

    def __str__(self):
        return self.text

    def clean(self):
        """Perform validation before saving."""
        super().clean()
        # Check that start date is before end date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be after start date.")

        # Check that linked object is set
        # 4. Add more checks here as needed
        if (
            self.object_type == AdvertisementObjectType.MAIN_PRODUCT_CATEGORY
            and self.main_product_category is None
        ):
            raise ValidationError("Must select a linked object.")

    class Meta:
        ordering = ["sort"]

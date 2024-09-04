from django.db import models

from api.models.main_product.add_on import AddOn
from common.models import BaseModel


class AddOnChoice(BaseModel):
    add_on = models.ForeignKey(
        AddOn,
        models.CASCADE,
        related_name="choices",
    )
    name = models.CharField(max_length=80)

    def __str__(self):
        return f"{self.add_on.main_product.name} - {self.add_on.name} - {self.name}"

    class Meta:
        verbose_name = "Variant Choice"
        verbose_name_plural = "Variants Choices"

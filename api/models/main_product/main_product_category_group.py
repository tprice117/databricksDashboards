from django.db import models

from common.models import BaseModel


class MainProductCategoryGroup(BaseModel):
    name = models.CharField(max_length=80)
    sort = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product Category Group"
        verbose_name_plural = "Product Category Groups"

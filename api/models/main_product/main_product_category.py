from django.db import models

from common.models import BaseModel


class MainProductCategory(BaseModel):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sort = models.IntegerField()
    main_product_category_code = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

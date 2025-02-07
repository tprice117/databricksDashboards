from django.db import models

from common.models import BaseModel
from common.utils.get_file_path import get_file_path


class MainProductCategoryGroup(BaseModel):
    name = models.CharField(max_length=80)
    sort = models.IntegerField()
    icon = models.ImageField(upload_to=get_file_path, blank=True, null=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Product Category Group"
        verbose_name_plural = "Product Category Groups"

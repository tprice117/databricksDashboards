from django.db import models

from common.utils.get_file_path import get_file_path


class Industry(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=get_file_path, blank=True, null=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True, null=True)
    sort = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Industries"
        ordering = ["sort", "name"]

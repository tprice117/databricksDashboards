from django.db import models
from common.utils.get_file_path import get_file_path

from api.models.user.user_group import UserGroup


class Branding(models.Model):
    # Branding Settings
    account = models.OneToOneField(
        UserGroup, 
        on_delete=models.CASCADE,
        related_name="branding",
        blank=True,
        null=True,
        parent_link=True,
    )
    display_name = models.CharField(max_length=50, default='Downstream')
    logo = models.ImageField(
        upload_to=get_file_path, 
        blank=True,
        null=True,
    )
    primary = models.CharField(max_length=7, default='#018381')
    secondary = models.CharField(max_length=7, default='#044162')

    def __str__(self):
        return f"Branding{self.id}"
from django.db import models

from common.models import BaseModel


class UserAddressType(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

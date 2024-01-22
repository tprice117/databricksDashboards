from django.db import models

from api.models.user.user import User
from api.models.user.user_address import UserAddress
from common.models import BaseModel


class UserUserAddress(BaseModel):
    user = models.ForeignKey(User, models.CASCADE)
    user_address = models.ForeignKey(UserAddress, models.CASCADE)

    def __str__(self):
        return f"{self.user.email} - {self.user_address.street}"

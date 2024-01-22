from django.db import models

from api.models.seller.seller_location import SellerLocation
from api.models.user.user import User
from common.models import BaseModel


class UserSellerLocation(BaseModel):
    user = models.ForeignKey(User, models.CASCADE)
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE)

    def __str__(self):
        return f"{self.user.email} - {self.seller_location.name}"

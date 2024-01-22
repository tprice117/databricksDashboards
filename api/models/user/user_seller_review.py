from django.db import models

from api.models.seller.seller import Seller
from api.models.user.user import User
from common.models import BaseModel


class UserSellerReview(BaseModel):  # added this model 2/25/2023 by Dylan
    seller = models.ForeignKey(
        Seller, models.DO_NOTHING, related_name="user_seller_review"
    )
    user = models.ForeignKey(User, models.DO_NOTHING, related_name="user_seller_review")
    title = models.CharField(max_length=255)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.seller.name} - {self.rating if self.rating else ""}'

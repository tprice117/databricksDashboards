from django.db import models

from api.models.choices.user_type import UserType
from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupPolicyPurchaseApproval(BaseModel):
    """
    Allows UserGroup Admins to better manage account spending by setting
    an order amount that requires approval. This limit is used to restrict
    (but not prevent, if the request is approved by an Admin) the amount of
    money that can be spent by the UserGroup in a single order.

    The only UserTypes that can be set are Billing Manager and Member.
    """

    user_group = models.OneToOneField(UserGroup, models.CASCADE)
    user_type = models.CharField(
        max_length=255,
        choices=UserType.choices,
    )
    amount = models.IntegerField()

    unique_together = ("user_group", "user_type")

    def __str__(self):
        return f"{self.user_group.name} - {self.user_type} - {self.amount}"

    # Only allow the UserType to be set to Billing Manager or Member, not Admin.
    def save(self, *args, **kwargs):
        if self.user_type == UserType.ADMIN:
            raise ValueError("UserType cannot be set to Admin.")
        super().save(*args, **kwargs)

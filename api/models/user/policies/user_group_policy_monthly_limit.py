from django.db import models

from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupPolicyMonthlyLimit(BaseModel):
    """
    Allows UserGroup Admins to set a monthly limit for the UserGroup.
    This limit is used to restrict the amount of money that can be spent
    by the UserGroup in a month. Orders placed on a credit card or
    via invoice are included in this limit.
    """

    user_group = models.OneToOneField(
        UserGroup,
        models.CASCADE,
        related_name="user_group_policy_monthly_limit",
    )
    amount = models.IntegerField()

    def __str__(self):
        return f"{self.user_group.name} - {self.amount}"

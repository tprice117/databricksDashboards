from django.db import models

from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupCreditApplication(BaseModel):
    user_group = models.ForeignKey(
        UserGroup, models.CASCADE, related_name="credit_applications"
    )
    requested_credit_limit = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )

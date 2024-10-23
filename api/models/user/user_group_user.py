from django.db import models

from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupUser(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE)

    def __str__(self):
        return f"{self.user_group.name} - {self.user.email}"

    class Meta:
        verbose_name = "Account User"
        verbose_name_plural = "Account Users"

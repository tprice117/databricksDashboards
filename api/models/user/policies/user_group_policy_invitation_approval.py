from django.db import models

from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupPolicyInvitationApproval(BaseModel):
    """
    When inviting new members to join your account, pick which
    roles need to have their invitation approved. This is useful
    for UserGroup Admins to control who can join the UserGroup.

    The only UserTypes that can be set are Billing Manager and Member.
    """

    user_group = models.OneToOneField(UserGroup, models.CASCADE)
    amount = models.IntegerField()

    def __str__(self):
        return f"{self.user_group.name} - {self.amount}"

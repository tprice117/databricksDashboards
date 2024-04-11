from django.db import models

from api.models.choices.user_type import UserType
from api.models.user.user_group import UserGroup
from common.models import BaseModel


class UserGroupPolicyInvitationApproval(BaseModel):
    """
    When inviting new members to join your account, pick which
    roles need to have their invitation approved. This is useful
    for UserGroup Admins to control who can join the UserGroup.

    The only UserTypes that can be set are Billing Manager and Member.
    """

    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="user_group_policy_invitation_approvals",
    )
    user_type = models.CharField(
        max_length=255,
        choices=[
            (
                UserType.BILLING.value,
                UserType.BILLING.label,
            ),
            (
                UserType.MEMBER.value,
                UserType.MEMBER.label,
            ),
        ],
    )

    class Meta:
        unique_together = ("user_group", "user_type")

    def __str__(self):
        return f"{self.user_group.name} - {self.user_type}"

from django.db import models

from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus


class UserGroupAdminApprovalUserInvite(BaseModel):
    """
    When the UserGroupPolicyInvitationApproval policy dictates, any User
    created by BillingManager or Member users will create an instance of this
    object. After Admin approval, a User will be created and invited to the
    UserGroup.
    """

    user_group = models.ForeignKey(
        UserGroup,
        models.CASCADE,
        related_name="user_group_admin_approval_user_invites",
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        blank=True,
        null=True,
    )
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    created_by = models.ForeignKey(
        User,
        models.CASCADE,
        related_name="user_group_admin_approval_user_invites",
    )

    class Meta:
        verbose_name = "User Invite Approval"
        verbose_name_plural = "User Invite Approvals"
        unique_together = ("user_group", "email")

    def __str__(self):
        return f"{self.user_group.name} - {self.amount}"

    # Pre/post save, check Status.
    # 1. If Status changes from PENDING to APPROVED, create a new User (which should trigger an invite email),
    # save that user to the UserGroupApprovalUserInvite.User field.
    # 2. If the Status changes from PENDING to DECLINED, update Status, then send email to "created_by" user with update.
    # 3. Do not allow any changes to be made if either the Status == DECLINED or Status == APPROVED.

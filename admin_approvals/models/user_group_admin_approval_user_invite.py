import logging

from django.db import models
from django.template.loader import render_to_string

from api.models.track_data import track_data
from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus
from common.models.choices.user_type import UserType
from notifications.utils.add_email_to_queue import add_email_to_queue

logger = logging.getLogger(__name__)


@track_data("status")
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
    type = models.CharField(
        max_length=255,
        choices=UserType.choices,
        default=UserType.ADMIN,
    )
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
        return f"{self.user_group.name} - {self.email}"

    def save(self, *args, **kwargs):
        """Saves the object to the db if the created_by user is an ADMIN or if the UserGroup has a policy that requires approval.
        Otherwise the User is created and this object is not saved to the db."""
        old_status = self.old_value("status")
        save_object = True
        # https://docs.djangoproject.com/en/4.2/ref/models/instances/#django.db.models.Model._state
        if self._state.adding is True:
            # Object just created
            if self.created_by.type == "ADMIN":
                self.status = ApprovalStatus.APPROVED
                # Admin is creating a user, so do not save the object to the db.
                save_object = False
            elif hasattr(self.user_group, "policy_invitation_approvals"):
                policy = self.user_group.policy_invitation_approvals.filter(
                    user_type=self.created_by.type
                ).first()
                if policy is not None:
                    self.status = ApprovalStatus.PENDING
                else:
                    # No policy exists for this user type, so do not save the object to the db.
                    save_object = False

        if old_status == ApprovalStatus.PENDING:
            if self.status == ApprovalStatus.APPROVED:
                # If Status changes from PENDING to APPROVED, create a new User (which should trigger an invite email),
                # save that user to the UserGroupApprovalUserInvite.User field.
                self.user = User.objects.create(
                    email=self.email,
                    username=self.email,
                    user_group_id=self.user_group_id,
                    type=UserType.MEMBER,
                )
            elif old_status == ApprovalStatus.DECLINED:
                # If the Status changes from PENDING to DECLINED, update Status, then send email to "created_by" user with update.
                logger.warning(
                    f"Admin Declined Invitation of User: [{self.email}] to Company: [{self.user_group.name}]"
                )
                # Send email to "created_by" user with update.
                subject = f"Admin Declined Invitation of User: [{self.email}] to Company: [{self.user_group.name}]"
                html_content = render_to_string(
                    "admin_approvals/emails/invite_update.min.html",
                    {
                        "invite_email": self.email,
                        "first_name": self.created_by.first_name,
                        "user_group_name": self.user_group.name,
                        "is_approved": False,
                    },
                )
                add_email_to_queue(
                    from_email="system@trydownstream.com",
                    to_emails=[self.created_by.email],
                    subject=subject,
                    html_content=html_content,
                )

        # Only allow changes to be made if the Status == PENDING.
        if self.old_value("status") == ApprovalStatus.PENDING and save_object:
            super().save(*args, **kwargs)

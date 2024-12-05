import logging

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from api.models.track_data import track_data
from api.models.user.user import User
from api.models.user.user_group import UserGroup
from common.models import BaseModel
from common.models.choices.approval_status import ApprovalStatus
from common.models.choices.user_type import UserType
from common.models.signals import base_model_pre_save
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
    phone = models.CharField(max_length=40, blank=True, null=True)
    type = models.CharField(
        max_length=255,
        choices=UserType.choices,
        default=UserType.ADMIN,
    )
    first_name = models.CharField(
        max_length=255,
    )
    last_name = models.CharField(
        max_length=255,
    )
    # This is used in the Auth0 login process to redirect the user to a specific page after login.
    # This is helpful in the account creation process to redirect the user to the correct
    # page after login (supplier, customer webapp).
    redirect_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL to redirect to after Auth0 login (defaults to webapp settings.BASE_URL).",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )

    class Meta:
        verbose_name = "User Invite Approval"
        verbose_name_plural = "User Invite Approvals"
        unique_together = ("user_group", "email")

    def __str__(self):
        return f"{self.user_group.name} - {self.email}"


@receiver(pre_save, sender=UserGroupAdminApprovalUserInvite)
def pre_save_user_group_admin_approval_order(
    sender, instance: UserGroupAdminApprovalUserInvite, **kwargs
):
    """
    Saves the object to the db if the created_by user is an ADMIN or if the UserGroup has a policy that requires approval.
    Otherwise the User is created and this object is not saved to the db.
    """
    old_status = instance.old_value("status")

    # Manually call the BaseModel pre_save signal. This is necessary because
    # by default, the pre_save signal for the BaseModel is called after the
    # pre_save signal for the UserGroupAdminApprovalUserInvite, resulting in
    # the created_by field not being set during this signal.
    if issubclass(sender, BaseModel):
        base_model_pre_save(sender, instance, **kwargs)

    # If old_status is not PENDING, throw an error.
    if not instance._state.adding and not old_status == ApprovalStatus.PENDING:
        raise ValueError(
            f"UserGroupAdminApprovalUserInvite cannot be updated once the Status is not PENDING. Current Status: {old_status}"
        )
    else:
        # The UserGroupAdminApprovalUserInvite.Status is PENDING. It's
        # either being created or updated.

        # Default source to "Referral from Coworker".
        source = User.Source.COWORKER

        if instance._state.adding and instance.created_by:
            is_admin = instance.created_by.type == UserType.ADMIN
            is_staff = instance.created_by.is_staff
            has_policy = (
                hasattr(instance.user_group, "policy_invitation_approvals")
                and instance.user_group.policy_invitation_approvals.filter(
                    user_type=instance.created_by.type
                ).first()
                is not None
            )

            if is_staff:
                # If the UserGroupAdminApprovalUserInvite is being created by a Staff
                # (internal Downstream) user, set the source to "Downstream Sales Rep".
                source = User.Source.SALES

            if is_admin or is_staff or not has_policy:
                # If the UserGroupAdminApprovalUserInvite is being created by an ADMIN
                # or a Staff (internal Downstream) user automatically approve the
                # UserGroupAdminApprovalUserInvite. Also, if there is no UserGroup User
                # Invite policy for the CreatedBy user type, automatically approve the
                # UserGroupAdminApprovalUserInvite.
                instance.status = ApprovalStatus.APPROVED

        if instance.status == ApprovalStatus.APPROVED:
            # If Status changes from PENDING to APPROVED (or was set to APPROVED above),
            # create a new User (which should trigger an invite email from Auth0),
            # save that user to the UserGroupApprovalUserInvite.User field.
            instance.user = User.objects.create(
                email=instance.email,
                phone=instance.phone,
                username=instance.email,
                user_group=instance.user_group,
                source=source,
                type=instance.type,
                first_name=instance.first_name,
                last_name=instance.last_name,
                redirect_url=instance.redirect_url,
            )
        elif old_status == ApprovalStatus.DECLINED:
            # If the Status changes from PENDING to DECLINED, update Status, then send email to "created_by" user with update.
            logger.warning(
                f"Admin Declined Invitation of User: [{instance.email}] to Company: [{instance.user_group.name}]"
            )
            # Send email to "created_by" user with update.
            subject = f"Admin Declined Invitation of User: [{instance.email}] to Company: [{instance.user_group.name}]"
            html_content = render_to_string(
                "admin_approvals/emails/invite_update.min.html",
                {
                    "invite_email": instance.email,
                    "first_name": instance.created_by.first_name,
                    "user_group_name": instance.user_group.name,
                    "is_approved": False,
                },
            )
            add_email_to_queue(
                from_email="system@trydownstream.com",
                to_emails=[instance.created_by.email],
                subject=subject,
                html_content=html_content,
            )

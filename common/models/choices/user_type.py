from django.db import models


class UserType(models.TextChoices):
    """
    User permission levels. Each level has increasing access to features.
    Member: Create, manage, and track projects. Place orders (with payment methods added by Billing Managers or Admins). UserGroups can have unlimited members.
    Billing Manager: Add/manage payment methods. Edit Billing details. UserGroups can have unlimited Billing Managers.
    Admin: Invite new members, remove members, or withdraw invitations sent to potential members. Create, manage, and track UserAddresses. Approval purchase requests (based on UserGroup Purchase policy). UserGroups can have unlimited Admins.
    """

    ADMIN = "ADMIN", "Admin"
    BILLING = "BILLING", "Billing Manager"
    MEMBER = "MEMBER", "Member"

from django.conf import settings
from django.contrib.auth.models import UserManager, BaseUserManager


class CustomerTeamManager(UserManager):
    def get_queryset(self):
        if settings.ENVIRONMENT == "TEST":
            # PROD: Downstream Team
            return (
                super()
                .get_queryset()
                .filter(user_group="bd49eaab-4b46-46c0-a9bf-bace2896b795")
            )
        else:
            # DEV: Customer Team #1 (CORE), Random Company
            return (
                super()
                .get_queryset()
                .filter(
                    user_group__in=[
                        "3e717df9-f811-4ddd-8d2f-a5f19b807321",
                        "38309b8e-0205-45dc-b12c-3bfa365825e2",
                    ]
                )
            )


class SalesTeamManager(BaseUserManager):
    # Using BaseUserManager instead of UserManager to avoid making a migration
    # Don't use to create new users, just to query users

    def get_queryset(self):
        if settings.ENVIRONMENT == "TEST":
            # PROD: Use "Sales" Group
            return (
                super()
                .get_queryset()
                .filter(groups__name="Sales", is_superuser=False)
                .distinct()
            )
        else:
            # DEV: Customer Team #1 (CORE)
            return (
                super()
                .get_queryset()
                .filter(
                    user_group__in=[
                        "3e717df9-f811-4ddd-8d2f-a5f19b807321",
                        "38309b8e-0205-45dc-b12c-3bfa365825e2",
                    ]
                )
            )

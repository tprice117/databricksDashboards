from django.db import models

from common.models.choices.user_type import UserType


class UserAddressQuerySet(models.QuerySet):
    def for_user(self, user, allow_all=True):
        if allow_all and user.is_staff:
            # Staff User: If User is Staff.
            return self.all()
        elif user.user_group and user.type == UserType.ADMIN:
            # Company Admin: If User is in a UserGroup and is Admin.
            return self.filter(user_group=user.user_group)
        elif user.user_group and user.type != UserType.ADMIN:
            # Company Non-Admin: If User is in a UserGroup and is not Admin.
            return self.filter(useruseraddress__user=user)
        else:
            # Individual User: If User is not in a UserGroup.
            return self.filter(user=user)


class UserAddressManager(models.Manager):
    def get_queryset(self):
        return UserAddressQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

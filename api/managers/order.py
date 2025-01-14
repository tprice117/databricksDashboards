from django.db import models

from common.models.choices.user_type import UserType


class OrderQuerySet(models.QuerySet):
    def for_user(self, user):
        self = self.prefetch_related("order_line_items")
        self = self.select_related("order_group__subscription")
        if user == "ALL" or user.is_staff:
            # Staff User: If User is Staff or "ALL".
            return self.all()
        elif user.user_group and user.type == UserType.ADMIN:
            # Company Admin: If User is in a UserGroup and is Admin.
            return self.filter(order_group__user__user_group=user.user_group)
        elif user.user_group and user.type != UserType.ADMIN:
            # Company Non-Admin: If User is in a UserGroup and is not Admin.
            return self.filter(order_group__user_address__useruseraddress__user=user)
        else:
            # Individual User: If User is not in a UserGroup.
            return self.filter(user=user)


class OrderManager(models.Manager):
    def get_queryset(self):
        return OrderQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

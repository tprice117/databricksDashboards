from django.db import models

from common.models.choices.user_type import UserType


class PushNotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        if user == "ALL" or user.is_staff:
            # Staff User: If User is Staff or "ALL".
            return self.all()
        elif user.user_group and user.type == UserType.ADMIN:
            # Company Admin: If User is in a UserGroup and is Admin.
            return self.filter(push_notification_tos__user__user_group=user.user_group)
        else:
            # Individual User: If User is not in a UserGroup.
            return self.filter(user=user)


class PushNotificationManager(models.Manager):
    def get_queryset(self):
        return PushNotificationQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

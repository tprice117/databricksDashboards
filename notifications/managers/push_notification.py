from django.db import models

from common.models.choices.user_type import UserType


class PushNotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        # pre-fetch_related("push_notification_tos")
        queryset = self.prefetch_related("push_notification_tos")
        if user == "ALL" or user.is_staff:
            # Staff User: If User is Staff or "ALL".
            queryset = self.all()
        elif user.user_group and user.type == UserType.ADMIN:
            # Company Admin: If User is in a UserGroup and is Admin.
            queryset = self.filter(
                push_notification_tos__user__user_group=user.user_group
            )
        else:
            # Individual User: If User is not in a UserGroup.
            queryset = self.filter(push_notification_tos__user=user)
        # Annotate is_read for this user.
        queryset = queryset.annotate(
            is_read=models.Case(
                models.When(
                    push_notification_tos__user=user,
                    then=models.F("push_notification_tos__is_read"),
                ),
                default=False,
                output_field=models.BooleanField(),
            )
        )
        return queryset


class PushNotificationManager(models.Manager):
    def get_queryset(self):
        return PushNotificationQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

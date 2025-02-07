from django.db import models


class PushNotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        # pre-fetch_related("push_notification_tos")
        queryset = self.prefetch_related("push_notification_tos")
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

from django.utils import timezone

from api.models.user.user import User


class UpdateLastActiveMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        assert hasattr(
            request, "user"
        ), "The UpdateLastActivityMiddleware requires authentication middleware to be installed."
        if request.user.is_authenticated():
            User.objects.filter(user__id=request.user.id).update(
                last_active=timezone.now(),
            )

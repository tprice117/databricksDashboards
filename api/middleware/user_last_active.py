from django.utils import timezone

from api.models.user.user import User


class UpdateLastActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Update the last_active field of the user.
        if request.user and request.user.is_authenticated:
            User.objects.filter(id=request.user.id).update(
                last_active=timezone.now(),
            )

        return response

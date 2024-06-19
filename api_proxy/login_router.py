from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from api.models import User
from api.utils.utils import decrypt_string
from api.utils.auth0 import get_password_change_url
import logging

logger = logging.getLogger(__name__)


def post_login_router(request):
    """Redirect to the correct page after login."""
    next_url = request.session.get("next", None)
    if next_url:
        del request.session["next"]
        response = redirect(next_url)
        return response

    if request.user.is_anonymous:
        return redirect(reverse("admin:index"))
    if request.user.is_staff:
        return redirect(reverse("admin:index"))
    elif hasattr(request.user.user_group, "seller"):
        return redirect(reverse("supplier_bookings"))
    elif request.user.user_group:
        return redirect(reverse("customer_home"))
    else:
        # Show "Nothing to see here" page
        return HttpResponse("Nothing to see here")


def login_view(request):
    """Override Django's default login view to redirect to the correct page after login."""
    next_url = request.GET.get("next", None)
    if next_url:
        response = render(request, "admin/login.html")
        request.session["next"] = next_url
        return response
    else:
        return render(request, "admin/login.html")


def register_account_view(request: HttpRequest):
    key = request.GET.get("key", "")
    try:
        user_id = decrypt_string(key)
        user = User.objects.get(id=user_id)
        if user.user_id is not None:
            password_change_url = get_password_change_url(user.user_id)
            payload = {"url": password_change_url}
            return render(request, "user-invite-email.html", payload)
        else:
            raise Exception("User ID is None")
    except Exception as e:
        logger.error(f"register_account_view: [{e}]", exc_info=e)
        return HttpResponse("Server Error, please contact support@trydownstream.com")

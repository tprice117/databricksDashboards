from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.conf import settings
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
        return redirect(reverse("customer_home"))
    elif hasattr(request.user.user_group, "seller"):
        return redirect(reverse("supplier_bookings"))
    elif request.user.user_group:
        return redirect(reverse("customer_home"))
    else:
        # Show "Nothing to see here" page
        # TODO: Add page with links to the correct pages or simply redirect to app.
        # return HttpResponse("Nothing to see here")
        return redirect(reverse("customer_home"))


def login_view(request):
    """Override Django's default login view and set the query param `next`
    as a session variable, so that on post login redirect the correct page is loaded."""
    next_url = request.GET.get("next", None)
    if next_url:
        request.session["next"] = next_url
    # Grab the oidc_authentication_init and redirect directly to it instead of rendering the login page.
    return redirect(reverse("oidc_authentication_init"))


def login_redirect_view(request: HttpRequest):
    """Auth0 Tenant Login URI points here. Redirect to the correct page after login.
    Default to the {settings.BASE_URL}/login if no redirect_url is set."""
    user_id = request.session.get("user_id", None)
    if request.user.is_anonymous:
        logger.info(
            f"User is anonymous: {request} headers:[{request.headers}], cookies:[{request.COOKIES}], user_id:[{user_id}]"
        )
        if user_id:
            user = User.objects.get(id=user_id)
            if user.redirect_url:
                return redirect(user.redirect_url)
    else:
        logger.info(
            f"User is authenticated: redirect_url:{request.user.redirect_url}-{request} headers:[{request.headers}], cookies:[{request.COOKIES}], user_id:[{user_id}]"
        )
        if request.user.redirect_url:
            # TODO: Test this, but maybe it redirect_url should be deleted after use, so that subsequent
            # logins don't perform this, allowing the user to return to the last page they were on, on login.
            return redirect(request.user.redirect_url)
        else:
            return post_login_router(request)
    return redirect(f"{settings.BASE_URL}/login")


def register_account_view(request: HttpRequest):
    key = request.GET.get("key", "")
    try:
        user_id = decrypt_string(key)
        user = User.objects.get(id=user_id)
        if user.user_id is not None:
            password_change_url = get_password_change_url(user.user_id)
            request.session["user_id"] = str(user.id)
            return redirect(password_change_url)
        else:
            raise Exception("User ID is None")
    except Exception as e:
        logger.error(f"register_account_view: [{e}]", exc_info=e)
        return HttpResponse("Server Error, please contact support@trydownstream.com")

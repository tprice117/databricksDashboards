from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.conf import settings


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


def login_redirect_view(request):
    """Auth0 Tenant Login URI points here. Redirect to the correct page after login."""
    if request.user.is_anonymous:
        return redirect(settings.BASE_URL)
    else:
        if request.user.redirect_url:
            # TODO: Test this, but maybe it redirect_url should be deleted after use, so that subsequent
            # logins don't perform this, allowing the user to return to the last page they were on, on login.
            return redirect(request.user.redirect_url)
        else:
            return redirect(settings.BASE_URL)

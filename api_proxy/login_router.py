from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse


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

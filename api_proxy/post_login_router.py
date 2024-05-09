from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def post_login_router(request):
    if request.user.is_staff:
        return redirect(reverse("admin:index"))
    elif hasattr(request.user.user_group, "seller"):
        return redirect(reverse("supplier_dashboard"))
    else:
        # Show "Nothing to see here" page
        return HttpResponse("Nothing to see here")

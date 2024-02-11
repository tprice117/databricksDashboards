from django.conf import settings
from django.urls import reverse


def provider_logout(request):
    # See your provider's documentation for details on if and how this is
    # supported
    redirect_endpoint = settings.OIDC_OP_LOGOUT_ENDPOINT
    client_id = settings.OIDC_RP_CLIENT_ID
    return_to = request.build_absolute_uri(reverse("admin:index"))

    redirect_url = "{}?returnTo={}&client_id={}".format(
        redirect_endpoint, return_to, client_id
    )
    return redirect_url

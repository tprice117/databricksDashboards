import jwt
from django.conf import settings
from django.shortcuts import redirect


def authenticate(request):
    user_data = {
        # "avatarURL": request.user.avatar_url,  # optional, but preferred
        "email": request.user.email,
        "id": str(request.user.id),
        "name": f"{request.user.first_name} {request.user.last_name}",
    }

    # Get "companyID" and "redirect" parameters from the request.
    company_id = request.GET.get("companyID")
    redirect_url = request.GET.get("redirect")

    # Generate a signed JWT token with the user data.
    jwt_token = jwt.encode(
        user_data,
        key=settings.CANNY_JWT_SECRET,
        algorithm="HS256",
    )

    print(jwt_token.decode("utf-8"))
    print(settings.CANNY_JWT_SECRET)
    jwt_token_string = jwt_token.decode("utf-8")

    return redirect(
        f"https://canny.io/api/redirects/sso?companyID={company_id}&ssoToken={jwt_token_string}&redirect={redirect_url}",
    )

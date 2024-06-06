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
        f"https://canny.io/api/redirects/sso?ssoToken={jwt_token_string}&redirect=https://feedback.trydownstream.com",
    )

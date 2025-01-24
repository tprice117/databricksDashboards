from django.urls import include, path

urlpatterns = [
    path("v1/", include("notifications.api.v1.urls")),
]

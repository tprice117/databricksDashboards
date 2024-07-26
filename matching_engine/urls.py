from django.urls import include, path

urlpatterns = [
    path("v1/", include("matching_engine.api.v1.urls")),
]

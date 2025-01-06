from django.urls import path, include

import explore.api.v1.urls as urls

urlpatterns = [
    path("explore/v1/", include(urls)),
]

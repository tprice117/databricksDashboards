from django.urls import path

import explore.api.v1.views as views

urlpatterns = [
    path("recents/", views.RecentsView.as_view(), name="recents"),
]

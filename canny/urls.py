from django.urls import path

from canny import views

urlpatterns = [
    path("authenticate", views.authenticate),
]

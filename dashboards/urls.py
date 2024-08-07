from django.urls import path

from . import views

urlpatterns = [
    path(
        "",
        views.command_center,
        name="command_center",
    ),
]

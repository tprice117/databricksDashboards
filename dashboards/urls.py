from django.urls import path

from . import views

urlpatterns = [
    path("index/", views.index, name="index"),
    path("pbiimport/", views.pbiimport, name="pbiimport"),
    path("poatest/", views.poatest, name="poatest"),

    path(
        "",
        views.command_center,
        name="command_center",
    ),
]

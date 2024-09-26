from django.urls import path

from . import views
from .views_new.sales_leaderboard import sales_leaderboard

urlpatterns = [
    path("index/", views.index, name="index"),
    path("pbiimport/", views.pbiimport, name="pbiimport"),
    path(
        "",
        views.command_center,
        name="command_center",
    ),
    path(
        "sales-leaderboard/",
        sales_leaderboard,
        name="sales_leaderboard",
    ),
]

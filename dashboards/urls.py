from django.urls import path

from . import views
from .views_new.sales_leaderboard import sales_leaderboard

urlpatterns = [
    path("index/", views.index, name="index"),
    path("sales-dashboard/", views.sales_dashboard, name="sales_dashboard"),

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
    path(
        "payout-reconciliation/",
        views.payout_reconciliation,
        name="payout_reconciliation",
    ),

]

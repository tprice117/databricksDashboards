from django.urls import path

from . import views
from .views_new.sales_leaderboard import sales_leaderboard, user_sales_detail, user_sales_product_mix, user_sales_top_accounts

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
    path(
        "user-sales-detail/<uuid:user_id>/",
        user_sales_detail,
        name="user_sales_detail",
    ),
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-product-mix/",
        user_sales_product_mix,
        name="user_sales_product_mix",
    ),
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-top-accounts/",
        user_sales_top_accounts,
        name="user_sales_top_accounts",
    ),
]

from django.urls import path

from . import views
from .views_new.order_origination import order_origination
from .views_new.sales_leaderboard import *

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
        "order-origination/",
        order_origination,
        name="order_origination",
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
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-new-accounts/",
        user_sales_new_accounts,
        name="user_sales_new_accounts",
    ),
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-churned-accounts/",
        user_sales_churned_accounts,
        name="user_sales_churned_accounts",
    ),
    path(
        "export_sales_dashboard_csv/",
        views.export_sales_dashboard_csv,
        name="export_sales_dashboard_csv",
    ),
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-28-day-list/",
        user_sales_28_day_list,
        name="user_sales_28_day_list",
    ),
    path(
        "user-sales-detail/<uuid:user_id>/user-sales-new-buyers/",
        user_sales_new_buyers,
        name="user_sales_new_buyers",
    ),
]

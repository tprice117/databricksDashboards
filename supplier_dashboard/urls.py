from django.urls import path

from . import views

urlpatterns = [
    path(
        "supplier/<uuid:supplier_id>/dashboard/",
        views.supplier_digest_dashboard,
        name="supplier_dashboard",
    ),
    path(
        "supplier/<uuid:supplier_id>/status/<str:status>/",
        views.supplier_digest_dashboard,
        name="supplier_dashboard",
    ),
    path("supplier/search/", views.supplier_search, name="supplier_search"),
    path(
        "supplier/impersonation/start/",
        views.supplier_impersonation_start,
        name="supplier_impersonation_start",
    ),
    path(
        "supplier/impersonation/stop/",
        views.supplier_impersonation_stop,
        name="supplier_impersonation_stop",
    ),
    path("supplier/", views.index, name="supplier_home"),
    path("supplier/logout/", views.supplier_logout, name="supplier_logout"),
    path("supplier/profile/", views.profile, name="supplier_profile"),
    path("supplier/company/", views.company, name="supplier_company"),
    path("supplier/users/", views.users, name="supplier_users"),
    path(
        "supplier/user/<uuid:user_id>/",
        views.user_detail,
        name="supplier_user_detail",
    ),
    path("supplier/user/new/", views.new_user, name="supplier_new_user"),
    path("supplier/bookings/", views.bookings, name="supplier_bookings"),
    path(
        "supplier/bookings/download/",
        views.download_bookings,
        name="supplier_bookings_download",
    ),
    path(
        "supplier/booking/<uuid:order_id>/",
        views.booking_detail,
        name="supplier_booking_detail",
    ),
    path(
        "supplier/chat/<uuid:conversation_id>/",
        views.chat,
        name="supplier_chat",
    ),
    path(
        "supplier/order/<uuid:order_id>/accept/",
        views.update_order_status,
        {"accept": True},
        name="supplier_order_accept",
    ),
    path(
        "supplier/order/<uuid:order_id>/complete/",
        views.update_order_status,
        {"complete": True, "accept": None},
        name="supplier_order_complete",
    ),
    path(
        "supplier/order/<uuid:order_id>/deny/",
        views.update_order_status,
        {"accept": False},
        name="supplier_order_deny",
    ),
    path(
        "supplier/booking/<uuid:order_id>/update/",
        views.update_booking_status,
        name="supplier_booking_update",
    ),
    path("supplier/payouts/", views.payouts, name="supplier_payouts"),
    path(
        "supplier/payouts/metrics/",
        views.payouts_metrics,
        name="supplier_payouts_metrics",
    ),
    path(
        "supplier/payouts/download/",
        views.download_payouts,
        name="supplier_payouts_download",
    ),
    path(
        "supplier/payout/<uuid:payout_id>/",
        views.payout_detail,
        name="supplier_payout_detail",
    ),
    path(
        "supplier/payout/<uuid:payout_id>/invoice/",
        views.payout_invoice,
        name="supplier_payout_invoice",
    ),
    path("supplier/locations/", views.locations, name="supplier_locations"),
    path(
        "supplier/locations/download/",
        views.download_locations,
        name="supplier_locations_download",
    ),
    path(
        "supplier/location/<uuid:location_id>/",
        views.location_detail,
        name="supplier_location_detail",
    ),
    path(
        "supplier/received_invoices/",
        views.received_invoices,
        name="supplier_received_invoices",
    ),
    path(
        "supplier/received_invoice/<uuid:invoice_id>/",
        views.received_invoice_detail,
        name="supplier_received_invoice_detail",
    ),
    path(
        "supplier/messages/clear/", views.messages_clear, name="supplier_messages_clear"
    ),
]

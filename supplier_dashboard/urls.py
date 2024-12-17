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
    path(
        "supplier/last_order/",
        views.supplier_last_order,
        name="supplier_last_order",
    ),
    path("supplier/search/", views.supplier_search, name="supplier_search"),
    path(
        "supplier/search/selection/",
        views.supplier_search,
        {"is_selection": True},
        name="supplier_search_selection",
    ),
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
    path("supplier/company/new/", views.new_company, name="supplier_new_company"),
    path("supplier/companies/", views.companies, name="supplier_companies"),
    path("supplier/users/", views.users, name="supplier_users"),
    path(
        "supplier/user/<uuid:user_id>/",
        views.user_detail,
        name="supplier_user_detail",
    ),
    path(
        "supplier/user/<uuid:user_id>/reset_password/",
        views.user_reset_password,
        name="supplier_reset_password",
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
    path("supplier/listings/", views.listings, name="supplier_listings"),
    # path(
    #     "supplier/listing/<uuid:listing_id>/",
    #     views.listing_detail,
    #     name="supplier_listing_detail",
    # ),
    path("supplier/products", views.products, name="supplier_products"),
    path(
        "supplier/products/category/<uuid:category_id>/",
        views.products_2,
        name="supplier_products_2",
    ),
    path(
        "supplier/products/locations/<uuid:main_product_id>/",
        views.products_3,
        name="supplier_products_3",
    ),
    path(
        "supplier/products/locations/<uuid:main_product_id>/form",
        views.products_3_table,
        name="supplier_products_3_table",
    ),
    path(
        "supplier/messages/unread/",
        views.get_intercom_unread_conversations,
        name="supplier_unread_conversations",
    ),
    path(
        "supplier/booking/<uuid:order_id>/chat/",
        views.chat,
        name="supplier_booking_chat",
    ),
    path(
        "supplier/chat/<str:conversation_id>/",
        views.chat,
        name="supplier_chat",
    ),
    path(
        "supplier/booking/<uuid:order_id>/customer/chat/",
        views.chat,
        {"is_customer": True},
        name="supplier_booking_customer_chat",
    ),
    path(
        "supplier/chat/<str:conversation_id>/customer/",
        views.chat,
        {"is_customer": True},
        name="supplier_customer_chat",
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
        "supplier/location/<uuid:seller_location_id>/user/<uuid:user_id>/",
        views.seller_location_user_add,
        name="supplier_location_add_user",
    ),
    path(
        "supplier/location/<uuid:seller_location_id>/user/<uuid:user_id>/remove/",
        views.seller_location_user_remove,
        name="supplier_location_remove_user",
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
    path(
        "supplier/conversation/new/webhook/",
        views.intercom_new_conversation_webhook,
        name="supplier_conversation_new_webhook",
    ),
]

from django.urls import path

from . import views

urlpatterns = [
    path("customer/search/", views.customer_search, name="customer_search"),
    path(
        "customer/search/selection/",
        views.customer_search,
        {"is_selection": True},
        name="customer_search_selection",
    ),
    path(
        "customer/user_address/search/",
        views.user_address_search,
        name="customer_user_address_search",
    ),
    path("customer/", views.index, name="customer_home"),
    path("customer/logout/", views.customer_logout, name="customer_logout"),
    path("customer/profile/", views.profile, name="customer_profile"),
    path("customer/company/", views.company_detail, name="customer_company"),
    path(
        "customer/credit_application/",
        views.credit_application,
        name="customer_credit_application",
    ),
    path("customer/order/add/", views.index, name="customer_new_order"),
    path("customer/order_groups/", views.my_order_groups, name="customer_order_groups"),
    path(
        "customer/order_group/<uuid:order_group_id>/",
        views.order_group_detail,
        name="customer_order_group_detail",
    ),
    path(
        "customer/order_group/<uuid:order_group_id>/swap/",
        views.order_group_swap,
        name="customer_order_group_swap",
    ),
    path(
        "customer/order_group/<uuid:order_group_id>/removal/",
        views.order_group_swap,
        {"is_removal": True},
        name="customer_order_group_removal",
    ),
    path(
        "customer/order/<uuid:order_id>/",
        views.order_detail,
        name="customer_order_detail",
    ),
    path(
        "customer/order/review/",
        views.order_review_form,
        name="customer_order_review_form",
    ),
    path(
        "customer/order/review/swap/",
        views.order_review_swap,
        name="customer_order_review_swap",
    ),
    path(
        "customer/company/last_order/",
        views.company_last_order,
        name="customer_company_last_order",
    ),
    path("customer/locations/", views.locations, name="customer_locations"),
    path(
        "customer/location/<uuid:location_id>/",
        views.location_detail,
        name="customer_location_detail",
    ),
    path(
        "customer/location/<uuid:user_address_id>/user/<uuid:user_id>/",
        views.customer_location_user_add,
        name="customer_location_user_add",
    ),
    path(
        "customer/location/<uuid:user_address_id>/user/<uuid:user_id>/remove/",
        views.customer_location_user_remove,
        name="customer_location_user_remove",
    ),
    path("customer/location/new/", views.new_location, name="customer_new_location"),
    path("customer/users/", views.users, name="customer_users"),
    path(
        "customer/user/<uuid:user_id>/associated_locations/",
        views.user_associated_locations,
        name="customer_user_associated_locations",
    ),
    path(
        "customer/user/<uuid:user_id>/",
        views.user_detail,
        name="customer_user_detail",
    ),
    path(
        "customer/user/<uuid:user_id>/reset_password/",
        views.user_reset_password,
        name="customer_reset_password",
    ),
    path(
        "customer/user/<uuid:user_id>/update_email/",
        views.user_update_email,
        name="customer_update_email",
    ),
    path("customer/user/new/", views.new_user, name="customer_new_user"),
    path(
        "customer/company/<uuid:user_group_id>/user/new/",
        views.company_new_user,
        name="customer_new_company_user",
    ),
    path("customer/invoices/", views.invoices, name="customer_invoices"),
    path(
        "customer/invoice/<uuid:invoice_id>/",
        views.invoice_detail,
        name="customer_invoice_detail",
    ),
    path("customer/company/new/", views.new_company, name="customer_new_company"),
    path("customer/email/check/", views.user_email_check, name="customer_email_check"),
    path("customer/companies/", views.companies, name="customer_companies"),
    path(
        "customer/company/<uuid:user_group_id>/",
        views.company_detail,
        name="customer_company_detail",
    ),
    path(
        "customer/impersonation/start/",
        views.customer_impersonation_start,
        name="customer_impersonation_start",
    ),
    path(
        "customer/impersonation/stop/",
        views.customer_impersonation_stop,
        name="customer_impersonation_stop",
    ),
    # NEW ORDER #
    path("customer/order/new/", views.new_order, name="customer_new_order"),
    path(
        "customer/order/category/<uuid:category_id>/price/",
        views.new_order_category_price,
        name="customer_category_price",
    ),
    path(
        "customer/order/new/product/<uuid:category_id>/",
        views.new_order_2,
        name="customer_new_order_2",
    ),
    path(
        "customer/order/new/options/<uuid:product_id>/",
        views.new_order_3,
        name="customer_new_order_3",
    ),
    path(
        "customer/order/new/suppliers/",
        views.new_order_4,
        name="customer_new_order_4",
    ),
    path(
        "customer/cart/send_quote/",
        views.cart_send_quote,
        name="customer_cart_send_quote",
    ),
    # POST: Create OrderGroup and loads cart. GET: Load cart #
    path(
        "customer/cart/",
        views.new_order_5,
        name="customer_cart",
    ),
    # POST
    path(
        "customer/new_bundle/",
        views.new_bundle,
        name="new_bundle",
    ),
    # GET/POST
    path(
        "customer/cart/<uuid:order_id>/date/edit/",
        views.customer_cart_date_edit,
        name="customer_cart_date_edit",
    ),
    # GET/POST
    path(
        "customer/cart/<uuid:order_group_id>/po/",
        views.customer_cart_po,
        name="customer_cart_po",
    ),
    # GET
    path(
        "customer/cart/<uuid:order_group_id>/po/edit/",
        views.customer_cart_po_edit,
        name="customer_cart_po_edit",
    ),
    path(
        "customer/cart/<uuid:order_group_id>/remove/",
        views.new_order_6,
        name="customer_new_order_6_remove",
    ),
    path(
        "customer/checkout/<uuid:user_address_id>/terms/",
        views.checkout_terms_agreement,
        name="customer_checkout_terms_agreement",
    ),
    path(
        "customer/checkout/<uuid:user_address_id>/",
        views.checkout,
        name="customer_checkout",
    ),
    path(
        "customer/order_group/<uuid:order_group_id>/attachments/edit/",
        views.edit_attachments,
        name="customer_order_group_edit_attachments",
    ),
    path(
        "customer/cart/quote/",
        views.show_quote,
        name="customer_show_quote",
    ),
    path(
        "customer/<uuid:user_address_id>/<uuid:payment_method_id>/default/payment/",
        views.make_payment_method_default,
        name="customer_default_payment_method",
    ),
    path(
        "customer/<uuid:payment_method_id>/remove/payment/",
        views.remove_payment_method,
        name="customer_remove_payment_method",
    ),
    path(
        "customer/payment/<uuid:payment_method_id>/status/",
        views.update_payment_method_status,
        name="customer_update_payment_method_status",
    ),
    path(
        "customer/new/payment/",
        views.add_payment_method,
        name="customer_new_payment",
    ),
    path(
        "customer/bookings/page/settings/",
        views.bookings_page_settings,
        name="customer_bookings_page_settings",
    ),
    path(
        "customer/reports/",
        views.reports,
        name="customer_reports",
    ),
    path("customer/reviews/", views.reviews, name="customer_reviews"),
    path("customer/leads/", views.leads, name="customer_leads"),
    path(
        "customer/leads/board/",
        views.leads_board,
        name="customer_leads_board",
    ),
    path(
        "customer/leads/<int:lead_id>/",
        views.leads_card,
        name="customer_leads_card",
    ),
    path(
        "customer/leads/new",
        views.leads_card_edit,
        {"lead_id": None},
        name="customer_leads_card_new",
    ),
    path(
        "customer/leads/<int:lead_id>/edit/",
        views.leads_card_edit,
        name="customer_leads_card_edit",
    ),
    path(
        "customer/lead/<int:lead_id>/",
        views.lead_detail,
        name="customer_lead_detail",
    ),
]

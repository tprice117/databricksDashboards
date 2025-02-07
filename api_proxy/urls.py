from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from rest_framework import routers

from api import views
from api_proxy import login_router

router = routers.DefaultRouter()
router.register(r"advertisements", views.AdvertisementViewSet)
router.register(
    r"disposal-location-waste-types", views.DisposalLocationWasteTypeViewSet
)
router.register(r"disposal-locations", views.DisposalLocationViewSet)
router.register(r"industries", views.IndustryViewSet)
router.register(r"sellers", views.SellerViewSet)
router.register(r"seller-locations", views.SellerLocationViewSet)
router.register(r"users", views.UserViewSet)
router.register(r"user-groups", views.UserGroupViewSet)
router.register(r"user-group-billings", views.UserGroupBillingViewSet)
router.register(
    r"user-group-credit-applications", views.UserGroupCreditApplicationViewSet
)
router.register(r"user-group-legal", views.UserGroupLegalViewSet)
router.register(r"user-user-addresses", views.UserUserAddressViewSet)
router.register(r"user-addresses", views.UserAddressViewSet)
router.register(r"user-address-types", views.UserAddressTypeViewSet)
router.register(r"add-on-choices", views.AddOnChoiceViewSet)
router.register(r"add-ons", views.AddOnViewSet)
router.register(r"main-product-add-ons", views.MainProductAddOnViewSet)
router.register(r"main-product-category-infos", views.MainProductCategoryInfoViewSet)
router.register(r"main-product-category-groups", views.MainProductCategoryGroupViewSet)
router.register(r"main-product-categories", views.MainProductCategoryViewSet)
router.register(r"main-product-infos", views.MainProductInfoViewSet)
router.register(r"main-products", views.MainProductViewSet)
router.register(r"main-products-page", views.MainProductPageViewSet)
router.register(r"main-product-waste-types", views.MainProductWasteTypeViewSet)
router.register(r"orders", views.OrderViewSet)
router.register(r"assets", views.assetViewSet)
router.register(r"order-groups", views.OrderGroupViewSet)
router.register(r"order-group-attachments", views.OrderGroupAttachmentViewSet)
router.register(r"order-line-items", views.OrderLineItemViewSet)
router.register(r"order-line-item-types", views.OrderLineItemTypeViewSet)
router.register(r"order-disposal-tickets", views.OrderDisposalTicketViewSet)
router.register(r"subscriptions", views.SubscriptionViewSet)
router.register(r"payouts", views.PayoutViewSet)
router.register(r"product-add-on-choices", views.ProductAddOnChoiceViewSet)
router.register(r"products", views.ProductViewSet)
router.register(r"seller-products", views.SellerProductViewSet)
router.register(
    r"seller-product-seller-locations", views.SellerProductSellerLocationViewSet
)
router.register(
    r"seller-product-seller-location-services",
    views.SellerProductSellerLocationServiceViewSet,
)
router.register(
    r"service-recurring-frequencies", views.ServiceRecurringFrequencyViewSet
)
router.register(
    r"main-product-service-recurring-frequencies",
    views.MainProductServiceRecurringFrequencyViewSet,
)
router.register(
    r"seller-product-seller-location-service-recurring-frequencies",
    views.SellerProductSellerLocationServiceRecurringFrequencyViewSet,
)
router.register(
    r"seller-product-seller-location-rentals",
    views.SellerProductSellerLocationRentalViewSet,
)
router.register(
    r"seller-product-seller-location-materials",
    views.SellerProductSellerLocationMaterialViewSet,
)
router.register(
    r"seller-product-seller-location-material-waste-types",
    views.SellerProductSellerLocationMaterialWasteTypeViewSet,
)
router.register(r"seller-invoice-payables", views.SellerInvoicePayableViewSet)
router.register(
    r"seller-invoice-payable-line-items", views.SellerInvoicePayableLineItemViewSet
)
router.register(r"waste-types", views.WasteTypeViewSet)
router.register(r"day-of-weeks", views.DayOfWeekViewSet)
router.register(r"time-slots", views.TimeSlotViewSet)

# Use-case-specific model endpoints.
router.register(r"user-addresses-for-seller", views.UserAddressesForSellerViewSet)
router.register(r"order-groups-for-seller", views.OrderGroupsForSellerViewSet)
router.register(r"orders-for-seller", views.OrdersForSellerViewSet)

urlpatterns = [
    # Login Redirect.
    path("", login_router.post_login_router, name="post_login_router"),
    path("login/redirect/", login_router.login_redirect_view, name="login_redirect"),
    path(
        "register/account/", login_router.register_account_view, name="register_account"
    ),
    path("admin/login/", login_router.login_view, name="login"),
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
    # START: API URLs.
    path("api/", include("api_proxy.api.v1.urls")),
    path("api/", include(router.urls)),
    # END: API URLs.
    # START: Schema URLs.
    path("api/schema/", views.SpectacularAPIViewNoAuth.as_view(), name="schema"),
    path(
        "api/schema/redoc/",
        views.SpectacularRedocViewNoAuth.as_view(url_name="schema"),
        name="redoc",
    ),
    path(
        "api/schema/swagger/",
        views.SpectacularSwaggerViewNoAuth.as_view(url_name="schema"),
        name="swagger",
    ),
    # END: Schema URLs.
    # START: Canny URLs.
    path("feedback/", include("canny.urls")),
    # END: Canny URLs.
    # Stripe.
    path("api/payment-methods/", views.StripePaymentMethods.as_view()),
    path("api/setup-intents/", views.StripeSetupIntents.as_view()),
    path("api/payment-intents/", views.StripePaymentIntents.as_view()),
    path(
        "api/customer-portal/<uuid:user_address_id>/", views.stripe_customer_portal_url
    ),
    path(
        "api/service-requests/<str:pk>/payout",
        views.StripeConnectPayoutForService.as_view(),
        name="payout",
    ),
    path("api/sessions", views.StripeCreateCheckoutSession.as_view()),
    # prediction ML
    path("api/prediction", views.Prediction.as_view(), name="predictions"),
    path("api/pricing/", views.get_pricing),
    # Stripe Dashboarding Endpoints
    path("api/stripe/connect/accounts", views.StripeConnectAccount.as_view()),
    path("api/stripe/connect/transfers", views.StripeConnectTransfer.as_view()),
    path("api/stripe/billing/invoices", views.StripeBillingInvoice.as_view()),
    path("api/stripe/billing/invoice-items", views.StripeBillingInvoiceItems.as_view()),
    path("api/stripe/billing/subscriptions", views.StripeBillingSubscription.as_view()),
    path("api/stripe/core/payment-intents", views.StripeCorePaymentIntents.as_view()),
    path("api/stripe/core/balance", views.StripeCoreBalance.as_view()),
    path(
        "api/stripe/core/balance-transactions",
        views.StripeCoreBalanceTransactions.as_view(),
    ),
    # Denver Compliance Endpoint.
    path("api/exports/denver-compliance/", views.denver_compliance_report),
    path("api/order/<uuid:order_id>/view/", views.order_status_view),
    path(
        "api/order/<uuid:order_id>/accept/", views.update_order_status, {"accept": True}
    ),
    path(
        "api/order/<uuid:order_id>/deny/", views.update_order_status, {"accept": False}
    ),
    # Supplier Dashboard.
    path("", include("supplier_dashboard.urls")),
    # Customer Dashboard.
    path("", include("customer_dashboard.urls")),
    # Explore.
    path("", include("explore.urls")),
    # Match Engine.
    path("matching-engine/", include("matching_engine.urls")),
    # Pricing Engine.
    path("pricing-engine/", include("pricing_engine.urls")),
    # Checkout.
    path("checkout/", include("cart.urls")),
    # Billing.
    path("billing/", include("billing.urls")),
    # API App URLs.
    path("api/", include("api.urls")),
    # Checkout.
    path("notifications/", include("notifications.urls")),
    # Dashboard URLs.
    path("dashboards/", include("dashboards.urls")),
    # Test.
    path("test/", views.test3),
    # invoice_payables URLS.
    path("invoice-payables/", include("invoice_payables.urls")),
    path("apple-app-site-association", views.apple_app_site_association),
    path(".well-known/apple-app-site-association", views.apple_app_site_association),
    path(".well-known/assetlinks.json", views.asset_link),
    # Robots.txt
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt",
            content_type="text/plain",
        ),
    ),
]

handler404 = "customer_dashboard.views.error_404"  # custom 404

handler500 = "customer_dashboard.views.error_500"  # custom 500

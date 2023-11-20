from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.views.generic import TemplateView
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register(r'disposal-location-waste-types', views.DisposalLocationWasteTypeViewSet, 'api')
router.register(r'disposal-locations', views.DisposalLocationViewSet, 'api')
router.register(r'sellers', views.SellerViewSet, 'api')
router.register(r'seller-locations', views.SellerLocationViewSet, 'api')
router.register(r'users', views.UserViewSet, 'api')
router.register(r'user-groups', views.UserGroupViewSet, 'api')
router.register(r'user-user-addresses', views.UserUserAddressViewSet, 'api')
router.register(r'user-seller-reviews', views.UserSellerReviewViewSet, 'api')
router.register(r'user-seller-review-aggregates', views.UserSellerReviewAggregateViewSet, 'api')
router.register(r'user-addresses', views.UserAddressViewSet, 'api')
router.register(r'user-address-types', views.UserAddressTypeViewSet, 'api')
router.register(r'add-on-choices', views.AddOnChoiceViewSet, 'api')
router.register(r'add-ons', views.AddOnViewSet, 'api')
router.register(r'main-product-add-ons', views.MainProductAddOnViewSet, 'api')
router.register(r'main-product-category-infos', views.MainProductCategoryInfoViewSet, 'api')
router.register(r'main-product-categories', views.MainProductCategoryViewSet, 'api')
router.register(r'main-product-infos', views.MainProductInfoViewSet, 'api')
router.register(r'main-products', views.MainProductViewSet, 'api')
router.register(r'main-product-waste-types', views.MainProductWasteTypeViewSet, 'api')
router.register(r'orders', views.OrderViewSet, 'api')
router.register(r'order-groups', views.OrderGroupViewSet, 'api')
router.register(r'order-line-items', views.OrderLineItemViewSet, 'api')
router.register(r'order-line-item-types', views.OrderLineItemTypeViewSet, 'api')
router.register(r'order-disposal-tickets', views.OrderDisposalTicketViewSet, 'api')
router.register(r'subscriptions', views.SubscriptionViewSet, 'api')
router.register(r'payouts', views.PayoutViewSet, 'api')
router.register(r'product-add-on-choices', views.ProductAddOnChoiceViewSet, 'api')
router.register(r'products', views.ProductViewSet, 'api')
router.register(r'seller-products', views.SellerProductViewSet, 'api')
router.register(r'seller-product-seller-locations', views.SellerProductSellerLocationViewSet, 'api')
router.register(r'seller-product-seller-location-services', views.SellerProductSellerLocationServiceViewSet, 'api')
router.register(r'service-recurring-frequencies', views.ServiceRecurringFrequencyViewSet, 'api')
router.register(r'main-product-service-recurring-frequencies', views.MainProductServiceRecurringFrequencyViewSet, 'api')
router.register(r'seller-product-seller-location-service-recurring-frequencies', views.SellerProductSellerLocationServiceRecurringFrequencyViewSet, 'api')
router.register(r'seller-product-seller-location-rentals', views.SellerProductSellerLocationRentalViewSet, 'api')
router.register(r'seller-product-seller-location-materials', views.SellerProductSellerLocationMaterialViewSet, 'api')
router.register(r'seller-product-seller-location-material-waste-types', views.SellerProductSellerLocationMaterialWasteTypeViewSet, 'api')
router.register(r'seller-invoice-payables', views.SellerInvoicePayableViewSet, 'api')
router.register(r'seller-invoices-payable-line-items', views.SellerInvoicePayableLineItemViewSet, 'api')
router.register(r'waste-types', views.WasteTypeViewSet, 'api')
router.register(r'day-of-weeks', views.DayOfWeekViewSet, 'api')
router.register(r'time-slots', views.TimeSlotViewSet, 'api')

# Use-case-specific model endpoints.
router.register(r'user-addresses-for-seller', views.UserAddressesForSellerViewSet, 'api')
router.register(r'order-groups-for-seller', views.OrderGroupsForSellerViewSet, 'api')
router.register(r'orders-for-seller', views.OrdersForSellerViewSet, 'api')

urlpatterns = [
    path('admin/', admin.site.urls),
    # Base API URL.
    path('api/', include(router.urls)),
    # Schema URLs.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ## Stripe.
    path('api/payment-methods/', views.StripePaymentMethods.as_view()),
    path('api/setup-intents/', views.StripeSetupIntents.as_view()),
    path('api/payment-intents/', views.StripePaymentIntents.as_view()),
    path('api/customer-portal/<uuid:user_address_id>/', views.stripe_customer_portal_url),
    path('api/service-requests/<str:pk>/payout', views.StripeConnectPayoutForService.as_view(), name="payout"),
    path('api/sessions', views.StripeCreateCheckoutSession.as_view()),
    path('api/order/pricing/<str:order_id>/', views.order_pricing),

    # prediction ML
    path('api/prediction', views.Prediction.as_view(), name="predictions"),
    path('api/pricing/', views.get_pricing),
    
    # add user test
    path('add_user/', views.AddUser.as_view(), name='add_user'),

    # Stripe Dashboarding Endpoints
    path('api/stripe/connect/accounts', views.StripeConnectAccount.as_view()),
    path('api/stripe/connect/transfers', views.StripeConnectTransfer.as_view()),
    path('api/stripe/billing/invoices', views.StripeBillingInvoice.as_view()),
    path('api/stripe/billing/subscriptions', views.StripeBillingSubscription.as_view()),    
    path('api/stripe/core/payment-intents', views.StripeCorePaymentIntents.as_view()),
    path('api/stripe/core/balance', views.StripeCoreBalance.as_view()),
    path('api/stripe/core/balance-transactions', views.StripeCoreBalanceTransactions.as_view()),

    # Denver Compliance Endpoint.
    path('api/exports/denver-compliance/',  views.denver_compliance_report),
]
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register(r'orders', views.OrderViewSet, 'api')
router.register(r'contacts', views.ContactViewSet, 'api')
router.register(r'accounts', views.AccountViewSet, 'api')
router.register(r'account-contacts', views.AccountContactViewSet, 'api')
router.register(r'opportunities', views.OpportunityViewSet, 'api')
router.register(r'main-product-categories', views.MainProductCategoryViewSet, 'api')
router.register(r'main-product-category-infos', views.ProductCategoryInfoViewSet, 'api')
router.register(r'main-products', views.MainProductViewSet, 'api')
router.register(r'main-product-infos', views.MainProductInfoViewSet, 'api')
router.register(r'products', views.ProductViewSet, 'api')
# router.register(r'main-product-frequencies', views.MainProductFrequencyViewSet, 'api')
router.register(r'price-books', views.PriceBookViewSet, 'api')
router.register(r'price-book-entries', views.PriceBookEntryViewSet, 'api')
router.register(r'main-product-add-ons', views.MainProductAddOnViewSet, 'api')
router.register(r'product-add-on-choices', views.ProductAddOnChoiceViewSet, 'api')
router.register(r'add-ons', views.AddOnViewSet, 'api')
router.register(r'add-on-choices', views.AddOnChoiceViewSet, 'api')
router.register(r'location-zones', views.LocationZoneViewSet, 'api')
router.register(r'postal-codes', views.PostalCodeViewSet, 'api')
router.register(r'pricebooks', views.PriceBookViewSet, 'api')
router.register(r'pricebook-entries', views.PriceBookEntryViewSet, 'api')

urlpatterns = [
    path('api/', include(router.urls)),
    # path('admin/', admin.site.urls),
    path('api/tasks/<int:pk>', views.TaskView.as_view()),
    path('api/tasks/', views.TaskView.as_view()),
    path('api/agents/<int:pk>', views.AgentView.as_view()),
    path('api/agents/', views.AgentView.as_view()),
    path('api/teams/<int:pk>', views.TeamView.as_view()),
    path('api/teams/', views.TeamView.as_view()),
    # path('manager/<int:pk>', views.ManagerView.as_view()),
    # path('manager/', views.ManagerView.as_view()),
    path('api/customers/<int:pk>', views.CustomerView.as_view()),
    path('api/customers/', views.CustomerView.as_view()),
    # path('merchant/<int:pk>', views.MerchantView.as_view()),
    # path('merchant/', views.MerchantView.as_view()),
    # path('mission/<int:pk>', views.MissionView.as_view()),
    # path('mission/', views.MissionView.as_view()),
    path('api/convert-sf-order-to-scrap-task/<str:pk>', views.ConvertSFOrderToScrapTask.as_view()),
    ## Stripe.
    path('api/payment-methods/', views.StripePaymentMethods.as_view()),
    path('api/setup-intents/', views.StripeSetupIntents.as_view()),
    path('api/payment-intents/', views.StripePaymentIntents.as_view()),
    path('api/service-requests/<str:pk>/payout', views.StripeConnectPayoutForService.as_view(), name="payout"),
    path('api/sessions', views.StripeCreateCheckoutSession.as_view()),

    # Stripe Dashboarding Endpoints
    path('api/stripe/connect/accounts', views.StripeConnectAccount.as_view()),
    path('api/stripe/connect/transfers', views.StripeConnectTransfer.as_view()),
    path('api/stripe/billing/invoices', views.StripeBillingInvoice.as_view()),
    path('api/stripe/billing/subscriptions', views.StripeBillingSubscription.as_view()),    
    path('api/stripe/core/payment-intents', views.StripeCorePaymentIntents.as_view()),
]
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.views.generic import TemplateView
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register(r'sellers', views.SellerViewSet, 'api')
router.register(r'seller-locations', views.SellerLocationViewSet, 'api')
router.register(r'users', views.UserViewSet, 'api')
router.register(r'user-user-addresses', views.UserUserAddressViewSet, 'api')
router.register(r'user-seller-reviews', views.UserSellerReviewViewSet, 'api')
router.register(r'user-addresses', views.UserAddressViewSet, 'api')
router.register(r'add-on-choices', views.AddOnChoiceViewSet, 'api')
router.register(r'add-ons', views.AddOnViewSet, 'api')
router.register(r'main-product-add-ons', views.MainProductAddOnViewSet, 'api')
router.register(r'main-product-category-infos', views.MainProductCategoryInfoViewSet, 'api')
router.register(r'main-product-categories', views.MainProductCategoryViewSet, 'api')
router.register(r'main-product-infos', views.MainProductInfoViewSet, 'api')
router.register(r'main-products', views.MainProductViewSet, 'api')
router.register(r'main-product-waste-types', views.MainProductWasteTypeViewSet, 'api')
router.register(r'order-details', views.OrderDetailsViewSet, 'api')
router.register(r'order-details-line-items', views.OrderDetailsLineItemViewSet, 'api')
router.register(r'subscriptions', views.SubscriptionViewSet, 'api')
router.register(r'orders', views.OrderViewSet, 'api')
router.register(r'product-add-on-choices', views.ProductAddOnChoiceViewSet, 'api')
router.register(r'products', views.ProductViewSet, 'api')
router.register(r'seller-products', views.SellerProductViewSet, 'api')
router.register(r'seller-product-seller-locations', views.SellerProductSellerLocationViewSet, 'api')
router.register(r'waste-types', views.WasteTypeViewSet, 'api')
router.register(r'dev-environ-test', views.DevEnvironTest, 'api')

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
    path('api/service-requests/<str:pk>/payout', views.StripeConnectPayoutForService.as_view(), name="payout"),
    path('api/sessions', views.StripeCreateCheckoutSession.as_view()),
]
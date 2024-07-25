from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import pricing_engine.api.v1.views as views

router = DefaultRouter()
router.register(
    r"pricing-engine/seller-product-seller-location-pricing",
    views.SellerProductSellerLocationPricingView,
)
router.register(
    r"pricing-engine/seller-product-seller-location-pricing-by-lat-long",
    views.SellerProductSellerLocationPricingByLatLongView,
)

urlpatterns = router.urls

from django.conf.urls import *
from rest_framework.routers import DefaultRouter

import matching_engine.api.v1.views as views

router = DefaultRouter()
router.register(
    r"matching-engine/seller-product-seller-locations",
    views.GetSellerProductSellerLocationsView,
    basename="matching-engine",
)
router.register(
    r"matching-engine/seller-product-seller-locations-by-lat-long",
    views.GetSellerProductSellerLocationsByLatLongView,
    basename="matching-engine",
)

urlpatterns = router.urls

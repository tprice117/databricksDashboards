from django.conf.urls import *
from django.urls import path

import pricing_engine.api.v1.views as views

urlpatterns = [
    path(
        "seller-product-seller-location-pricing/",
        views.SellerProductSellerLocationPricingView.as_view(),
    ),
    path(
        "seller-product-seller-location-pricing-by-lat-long",
        views.SellerProductSellerLocationPricingByLatLongView.as_view(),
    ),
]

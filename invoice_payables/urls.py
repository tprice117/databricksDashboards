from django.urls import path

from . import views

urlpatterns = [
    path("index/", views.index, name="index"),
    path("<uuid:id>/", views.invoice_detail, name="invoice_detail")
]

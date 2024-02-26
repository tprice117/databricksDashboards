from django.urls import path

import payments.api.v1.views as views

urlpatterns = [
    path("invoices/", views.invoices),
]

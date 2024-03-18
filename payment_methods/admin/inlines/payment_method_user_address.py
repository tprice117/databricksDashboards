from django.contrib import admin

from payment_methods.models import PaymentMethodUserAddress


class PaymentMethodUserAddressInline(admin.TabularInline):
    model = PaymentMethodUserAddress
    fields = ("user_address",)
    show_change_link = True
    extra = 0

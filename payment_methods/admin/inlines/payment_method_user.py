from django.contrib import admin

from payment_methods.models import PaymentMethodUser


class PaymentMethodUserInline(admin.TabularInline):
    model = PaymentMethodUser
    fields = ("user",)
    show_change_link = True
    extra = 0

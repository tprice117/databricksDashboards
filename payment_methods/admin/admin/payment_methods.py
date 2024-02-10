from django.contrib import admin

from payment_methods.models import PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        # If PaymentMethod is being edited,
        # show card fields (read-only).
        if obj:
            return self.readonly_fields + (
                "token",
                "card_number",
                "card_brand",
                "card_exp_month",
                "card_exp_year",
            )
        else:
            # If PaymentMethod is being added, don't show card fields.
            return self.readonly_fields

from django.contrib import admin

from api.models import Branding


class BrandingInline(admin.TabularInline):
    model = Branding
    fields = (
        "display_name",
        "logo",
        "primary",
        "secondary",
    )
    show_change_link = False
    extra = 0

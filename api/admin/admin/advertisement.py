from django.contrib import admin
from django import forms
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import Advertisement
from common.admin.admin.base_admin import BaseModelAdmin


class AdvertisementResource(resources.ModelResource):
    class Meta:
        model = Advertisement
        skip_unchanged = True


class AdvertisementAdminForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        fields = "__all__"
        widgets = {
            "text_color": forms.TextInput(attrs={"type": "color"}),
            "background_color": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields[
                "text_color"
            ].help_text += f" Currently: {self.instance.text_color}"
            self.fields[
                "background_color"
            ].help_text += f" Currently: {self.instance.background_color or 'None'}"


@admin.register(Advertisement)
class AdvertisementAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [AdvertisementResource]
    form = AdvertisementAdminForm
    search_fields = [
        "id",
        "text",
    ]
    # Add raw_id_fields for ForeignKey fields with many records to improve performance.
    raw_id_fields = ["main_product_category"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "text",
                    "image",
                    "sort",
                    "is_active",
                ]
            },
        ),
        (
            "Colors",
            {
                "fields": [
                    "background_color",
                    "text_color",
                ]
            },
        ),
        (
            "Linked Object",
            {
                "fields": [
                    "object_type",
                    "main_product_category",
                ]
            },
        ),
        (
            "Dates (Optional)",
            {
                "fields": [
                    "start_date",
                    "end_date",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]

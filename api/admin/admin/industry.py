from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources

from api.models import Industry
from django.forms.widgets import SelectMultiple


class UniqueSelectMultiple(SelectMultiple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = [(x, x) for x in set(self.choices)]


class MainProductCategoryInlines(admin.TabularInline):
    from api.models.main_product.main_product_category import MainProductCategory

    model = MainProductCategory.industry.through
    extra = 0

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        kwargs["widget"] = UniqueSelectMultiple
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class IndustryResource(resources.ModelResource):
    class Meta:
        model = Industry
        skip_unchanged = True


@admin.register(Industry)
class IndustryAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_classes = [IndustryResource]
    search_fields = [
        "id",
        "name",
        "description",
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "description",
                    "image",
                    "sort",
                ]
            },
        ),
    ]
    inlines = [MainProductCategoryInlines]

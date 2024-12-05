from django.contrib import admin

from api.models import SellerProductSellerLocation


class SellerProductSellerLocationInline(admin.TabularInline):
    model = SellerProductSellerLocation
    fields = ("seller_product", "total_inventory")
    raw_id_fields = ("seller_product",)
    show_change_link = True
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(SellerProductSellerLocationInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == "seller_product":
            if request._obj_ is not None:
                # print(request._obj_)
                # print(field.queryset)
                field.queryset = field.queryset.filter(seller=request._obj_.seller)
            else:
                field.queryset = field.queryset.none()
        return field

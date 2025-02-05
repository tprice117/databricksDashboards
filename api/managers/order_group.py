from django.db import models

from common.models.choices.user_type import UserType


class OrderGroupQuerySet(models.QuerySet):
    def for_user(self, user):
        self = self.prefetch_related(
            "orders__order_line_items",
            "user__user_group__credit_applications",
            "seller_product_seller_location__seller_product__product__product_add_on_choices",
            "seller_product_seller_location__seller_product__product__main_product__related_products",
        )
        self = self.select_related(
            "user",
            "user__user_group",
            "user_address",
            "waste_type",
            "time_slot",
            "service_recurring_frequency",
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product__main_product_category",
            "seller_product_seller_location__seller_location__seller",
        )
        if user == "ALL" or user.is_staff:
            # Staff User: If User is Staff or "ALL".
            return self.all()
        elif user.user_group and user.type == UserType.ADMIN:
            # Company Admin: If User is in a UserGroup and is Admin.
            return self.filter(user__user_group=user.user_group)
        elif user.user_group and user.type != UserType.ADMIN:
            # Company Non-Admin: If User is in a UserGroup and is not Admin.
            return self.filter(user_address__useruseraddress__user=user)
        else:
            # Individual User: If User is not in a UserGroup.
            return self.filter(user=user)


class OrderGroupManager(models.Manager):
    def get_queryset(self):
        return OrderGroupQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

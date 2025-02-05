from django.db import models


class MainProductQuerySet(models.QuerySet):
    def with_likes(self):
        return self.annotate(
            likes=models.Count(
                "products__seller_products__seller_product_seller_locations__order_groups__orders__review",
                filter=models.Q(
                    products__seller_products__seller_product_seller_locations__order_groups__orders__review__rating=True
                ),
                distinct=True,
            ),
        )

    def with_listings(self):
        return self.annotate(
            listings=models.Count(
                "products__seller_products__seller_product_seller_locations",
                distinct=True,
            ),
        )

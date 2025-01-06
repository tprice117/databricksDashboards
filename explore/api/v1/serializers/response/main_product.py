from rest_framework import serializers
from api.models import (
    MainProduct,
    OrderReview,
    SellerProductSellerLocation,
)


class ExploreMainProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)
    listings_count = serializers.SerializerMethodField(read_only=True)
    likes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MainProduct
        fields = ["id", "name", "description", "image", "listings_count", "likes_count"]

    def get_image(self, obj):
        if obj.image_del:
            return obj.image_del
        elif obj.main_product_category.icon:
            return obj.main_product_category.icon.url
        return None

    def get_listings_count(self, obj):
        return SellerProductSellerLocation.objects.filter(
            seller_product__product__main_product=obj
        ).count()

    def get_likes_count(self, obj):
        return OrderReview.objects.filter(
            order__order_group__seller_product_seller_location__seller_product__product__main_product=obj,
            rating=True,
        ).count()

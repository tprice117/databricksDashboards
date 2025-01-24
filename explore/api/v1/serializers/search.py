from rest_framework import serializers
from api.models import MainProduct, MainProductCategory


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        required=True,
        help_text="The search query. This will search MainProducts and MainProductCategories.",
    )


class MainProductSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainProduct
        fields = "__all__"


class MainProductCategorySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainProductCategory
        fields = "__all__"


class SearchSerializer(serializers.Serializer):
    main_products = MainProductSearchSerializer(many=True)
    main_product_categories = MainProductCategorySearchSerializer(many=True)

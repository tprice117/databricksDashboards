from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from api.models import MainProduct, MainProductCategory, MainProductCategoryGroup


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        required=True,
        help_text="The search query. This will search MainProducts and MainProductCategories.",
    )


class MainProductSearchSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = MainProduct
        fields = "__all__"

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj):
        """Get images as a list of urls."""
        images = obj.images.all()
        return [image.image.url for image in images]


class MainProductCategoryGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainProductCategoryGroup
        fields = ["id", "name", "icon", "sort"]


class MainProductCategorySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainProductCategory
        fields = "__all__"


class SearchSerializer(serializers.Serializer):
    main_products = MainProductSearchSerializer(many=True)
    main_product_categories = MainProductCategorySearchSerializer(many=True)
    main_product_category_groups = MainProductCategoryGroupSerializer(many=True)

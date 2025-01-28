from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)

from api.models import MainProduct, MainProductCategory, MainProductCategoryGroup
from explore.api.v1.serializers import SearchRequestSerializer, SearchSerializer


# Explore page
class SearchView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 60))  # Cache the view for 1 hour
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query. This will search MainProducts, MainProductCategories, and MainProductCategoryGroups.",
                required=True,
            ),
        ],
        request=SearchRequestSerializer,
        responses={
            200: SearchSerializer(),
        },
    )
    def get(self, request, *args, **kwargs):
        """Searches for matching MainProducts, MainProductCategories, and MainProductCategoryGroups."""
        # Convert request into serializer.
        serializer = SearchRequestSerializer(data=request.query_params)
        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        try:
            query = serializer.validated_data["q"]
            # Search for MainProducts, MainProductCategories, and MainProductCategoryGroups.
            main_products = (
                MainProduct.objects.filter(name__icontains=query)
                .prefetch_related("images")
                .order_by("sort")
            )
            # get a distinct list of category ids from main products
            category_ids = []
            for main_product in main_products:
                if main_product.main_product_category_id not in category_ids:
                    category_ids.append(main_product.main_product_category_id)
            main_product_categories = (
                MainProductCategory.objects.filter(
                    Q(name__icontains=query) | Q(id__in=category_ids)
                )
                .select_related("group")
                .order_by("sort")
            )
            main_product_category_groups = MainProductCategoryGroup.objects.filter(
                name__icontains=query
            ).order_by("sort")

            # Serialize the main products and categories
            data = SearchSerializer(
                {
                    "main_products": main_products,
                    "main_product_categories": main_product_categories,
                    "main_product_category_groups": main_product_category_groups,
                }
            ).data
            return Response(data)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        except Exception as e:
            raise APIException(str(e))

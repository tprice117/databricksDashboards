from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)

from api.models import MainProduct, MainProductCategory
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
                description="Search query. This will search MainProducts and MainProductCategories.",
                required=True,
            ),
        ],
        request=SearchRequestSerializer,
        responses={
            200: SearchSerializer(),
        },
    )
    def get(self, request, *args, **kwargs):
        """Searches for matching MainProducts and MainProductCategories."""
        # Convert request into serializer.
        serializer = SearchRequestSerializer(data=request.query_params)
        # serializer = SearchRequestSerializer(data=request.data)
        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        try:
            query = serializer.validated_data["q"]
            main_products = MainProduct.objects.filter(name__icontains=query)
            main_product_categories = MainProductCategory.objects.filter(
                name__icontains=query
            )
            # Serialize the main products and categories
            data = SearchSerializer(
                {
                    "main_products": main_products,
                    "main_product_categories": main_product_categories,
                }
            ).data
            return Response(data)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        except Exception as e:
            raise APIException(str(e))

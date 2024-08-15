from api.models.main_product.main_product import MainProduct
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation


def align_seller_product_seller_location_children_with_main_product(
    main_product: MainProduct,
    data: dict,
) -> dict:
    """
    Remove child SellerProductSellerLocation configurations that are not needed.
    For example, set the SellerProductSellerLocation.rental_multi_step to None,
    if the MainProduct.rental_multi_step is False.
    """

    # Rental One Step.
    if not main_product.has_rental_one_step and "rental_one_step" in data:
        data["rental_one_step"] = None

    # Rental Two Step.
    if not main_product.has_rental and "rental" in data:
        data["rental"] = None

    # Rental Multi Step.
    if not main_product.has_rental_multi_step and "rental_multi_step" in data:
        data["rental_multi_step"] = None

    # Service (Legacy).
    if not main_product.has_service and "service" in data:
        data["service"] = None

    # Service Times Per Week.
    if not main_product.has_service_times_per_week and "service_times_per_week" in data:
        data["service_times_per_week"] = None

    # Material.
    if not main_product.has_material and "material" in data:
        data["material"] = None

    return data

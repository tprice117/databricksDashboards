from api.models.seller.seller_product_seller_location import SellerProductSellerLocation


def align_seller_product_seller_location_children_with_main_product(
    seller_product_seller_location: SellerProductSellerLocation,
) -> SellerProductSellerLocation:
    """
    Remove child SellerProductSellerLocation configurations that are not needed.
    For example, set the SellerProductSellerLocation.rental_multi_step to None,
    if the MainProduct.rental_multi_step is False.
    """
    main_product = seller_product_seller_location.seller_product.product.main_product

    # Rental One Step.
    if not main_product.has_rental_one_step:
        seller_product_seller_location.rental_one_step = None

    # Rental Two Step.
    if not main_product.has_rental:
        seller_product_seller_location.rental = None

    # Rental Multi Step.
    if not main_product.has_rental_multi_step:
        seller_product_seller_location.rental_multi_step = None

    # Service (Legacy).
    if not main_product.has_service:
        seller_product_seller_location.service = None

    # Service Times Per Week.
    if not main_product.has_service_times_per_week:
        seller_product_seller_location.service_times_per_week = None

    # Material.
    if not main_product.has_material:
        seller_product_seller_location.material = None

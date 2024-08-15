from api.models.main_product.main_product import MainProduct
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from matching_engine.utils.align_seller_product_seller_location_children_with_main_product import (
    align_seller_product_seller_location_children_with_main_product,
)
from matching_engine.utils.seller_product_seller_location_plus_take_rate import (
    seller_product_seller_location_plus_take_rate,
)


def prep_seller_product_seller_locations_for_response(
    main_product: MainProduct,
    seller_product_seller_locations: SellerProductSellerLocation,
):
    # Add default take rate to the price and serialize the data.
    data_with_take_rate = []

    for seller_product_seller_location in seller_product_seller_locations:
        data_with_take_rate.append(
            seller_product_seller_location_plus_take_rate(
                seller_product_seller_location,
            )
        )

    # Align SellerProductSellerLocations pricing configurations with
    # current MainProduct settings.
    data_with_aligned_children_configs = [
        align_seller_product_seller_location_children_with_main_product(
            main_product=main_product,
            data=data,
        )
        for data in data_with_take_rate
    ]

    return data_with_aligned_children_configs

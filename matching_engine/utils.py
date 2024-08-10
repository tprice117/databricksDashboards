from typing import List

from api.models import SellerProductSellerLocation
from api.serializers import SellerProductSellerLocationSerializer


def seller_product_seller_location_plus_take_rate(
    seller_product_seller_location: SellerProductSellerLocation,
):
    """
    This function takes a SellerProductSellerLocation object returns a
    serialized SellerProductSellerLocation object with the price adjusted
    by the default_take_rate of the product.
    """
    data = SellerProductSellerLocationSerializer(
        seller_product_seller_location,
    ).data

    default_take_rate = (
        seller_product_seller_location.seller_product.product.main_product.default_take_rate
    )

    # Service.
    data = _update_if_exists(
        data=data,
        parent_key="service",
        child_keys=[
            "price_per_mile",
            "flat_rate_price",
        ],
        default_take_rate=default_take_rate,
    )

    # Service Times Per Week.
    data = _update_if_exists(
        data=data,
        parent_key="service_times_per_week",
        child_keys=[
            "one_time_per_week",
            "two_times_per_week",
            "three_times_per_week",
            "four_times_per_week",
            "five_times_per_week",
        ],
        default_take_rate=default_take_rate,
    )

    # Material.
    if "material" in data and "waste_types" in data["material"]:
        waste_types = data["material"]["waste_types"]

        # PRint the price_per_ton for each waste type.
        print("Before")
        for waste_type in waste_types:
            print(waste_type["price_per_ton"])

        # For all waste types, update the price_per_ton. Then replace the waste_types in the data.
        updated_waste_types = []
        for waste_type in waste_types:
            waste_type["price_per_ton"] = (
                waste_type["price_per_ton"] * (1 + (default_take_rate / 100))
                if waste_type["price_per_ton"]
                else None
            )
            updated_waste_types.append(waste_type)

        # PRint the price_per_ton for each waste type.
        print("After")
        for waste_type in updated_waste_types:
            print(waste_type["price_per_ton"])

        data["material"]["waste_types"] = updated_waste_types

    # Rental One Step.
    data = _update_if_exists(
        data=data,
        parent_key="rental_one_step",
        child_keys=[
            "rate",
        ],
        default_take_rate=default_take_rate,
    )

    # Rental Two Step.
    data = _update_if_exists(
        data=data,
        parent_key="rental",
        child_keys=[
            "price_per_day_included",
            "price_per_day_additional",
        ],
        default_take_rate=default_take_rate,
    )

    # Rental Multi Step.
    data = _update_if_exists(
        data=data,
        parent_key="rental_multi_step",
        child_keys=[
            "hour",
            "day",
            "week",
            "two_weeks",
            "month",
        ],
        default_take_rate=default_take_rate,
    )

    return data


def _update_if_exists(
    data,
    parent_key: str,
    child_keys: List[str],
    default_take_rate,
):
    """
    This function updates the child keys of a parent key in a dictionary
    if the parent key exists and the child key exists in the parent key.

    Note: default_take_rate is a float between 0 and 100.
    """

    for child_key in child_keys:
        if parent_key in data and data[parent_key] and child_key in data[parent_key]:
            data[parent_key][child_key] = (
                data[parent_key][child_key] * (1 + (default_take_rate / 100))
                if data[parent_key][child_key]
                else None
            )
    return data

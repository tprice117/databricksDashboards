from api.models.main_product.main_product_waste_type import MainProductWasteType
from api.models.main_product.product import Product
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.seller.seller_product_seller_location_material_waste_type import (
    SellerProductSellerLocationMaterialWasteType,
)
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from common.utils import DistanceUtils


class MatchingEngine:
    @staticmethod
    def get_possible_seller_product_seller_locations(
        product: Product,
        user_address: UserAddress,
        waste_type: WasteType = None,
    ) -> list[SellerProductSellerLocation]:
        # Get all SellerProductSellerLocation objects that match the product.
        seller_product_seller_locations = SellerProductSellerLocation.objects.filter(
            seller_product__product=product,
        )

        # For each SellerProductSellerLocation, check if the ServiceRadius covers the UserAddress.
        matches = []
        for seller_product_seller_location in seller_product_seller_locations:
            # Is the UserAddress within the ServiceRadius of the SellerProductSellerLocation?
            within_service_radius = MatchingEngine._customer_is_within_seller_product_seller_location_service_radius(
                seller_product_seller_location,
                user_address,
            )

            # Does the SellerProductSellerLocation match the WasteType of the Product?
            matches_waste_type = (
                MatchingEngine._seller_product_seller_location_matches_waste_type(
                    seller_product_seller_location,
                    waste_type,
                )
            )

            if within_service_radius and matches_waste_type:
                matches.append(seller_product_seller_location)

        return matches

    @staticmethod
    def rematch_seller_product_seller_location(
        order_group,
    ):
        """
        Find the "next" SellerProductSellerLocation for the OrderGroup.
        The "next" SellerProductSellerLocation covers the OrderGroup's UserAddress.
        The "next" SellerProductSellerLocation has a greater than or equal to OrderGroupRental.included_days value.
        The "next" SellerProductSellerLocation has a greater than or equal to OrderGroupMaterial.tonnage_included value.
        """
        # Get all possible SellerProductSellerLocations for the OrderGroup's UserAddress
        # (within serivce_radius), and Product.
        seller_product_seller_locations_within_service_radius = MatchingEngine.get_possible_seller_product_seller_locations(
            product=order_group.seller_product_seller_location.seller_product.product,
            user_address=order_group.user_address,
            waste_type=order_group.waste_type,
        )

        # Filter out SellerProductSellerLocations that do not have an equal or greater
        # included_days value or tonnage_included value.
        possible_seller_product_seller_locations = []
        order_group_has_rental = hasattr(order_group, "rental")
        order_group_has_material = hasattr(order_group, "material")

        for seller_product_seller_location in possible_seller_product_seller_locations:
            seller_product_seller_location_has_rental = hasattr(
                seller_product_seller_location, "rental"
            )
            seller_product_seller_location_has_material = hasattr(
                seller_product_seller_location, "material"
            )

            # Check whether the SellerProductSellerLocation and OrderGroup both have the rental
            # and material attributes.
            both_have_rental = (
                order_group_has_rental == seller_product_seller_location_has_rental
            )
            both_have_material = (
                order_group_has_material == seller_product_seller_location_has_material
            )

            # Check whether the SellerProductSellerLocation's included_days value is greater
            # than or equal to the OrderGroup's included_days value.
            included_days_is_equal_or_greater = not order_group_has_rental or (
                both_have_rental
                and seller_product_seller_location.rental.included_days
                >= order_group.rental.included_days
            )

            # Check whether the SellerProductSellerLocation's tonnage_included value is greater
            # than or equal to the OrderGroup's tonnage_quantity value.
            tonnage_included_is_equal_or_greater = not order_group_has_material or (
                both_have_material
                and seller_product_seller_location.tonnage_included
                >= order_group.tonnage_quantity
            )

            if (
                included_days_is_equal_or_greater
                and tonnage_included_is_equal_or_greater
            ):
                possible_seller_product_seller_locations.append(
                    seller_product_seller_location
                )

        if possible_seller_product_seller_locations.count() == 0:
            # If no possible SellerProductSellerLocations are found, return None.
            return None
        else:
            # Sort the SellerProductSellerLocations by the included_days value (fewest days first),
            # then by the tonnage_included value (fewest tons first).
            possible_seller_product_seller_locations.sort(
                key=lambda x: (x.included_days, x.tonnage_included)
            )

            # If there are possible SellerProductSellerLocations found, return the
            # SellerProductSellerLocation with the fewest included_days and tonnage_included.
            return possible_seller_product_seller_locations[0]

    def _customer_is_within_seller_product_seller_location_service_radius(
        seller_product_seller_location: SellerProductSellerLocation,
        user_address: UserAddress,
    ):
        distance = DistanceUtils.get_driving_distance(
            lat1=seller_product_seller_location.seller_location.latitude,
            lon1=seller_product_seller_location.seller_location.longitude,
            lat2=user_address.latitude,
            lon2=user_address.longitude,
        )

        return float(distance) < float(
            seller_product_seller_location.service_radius or 0
        )

    def _seller_product_seller_location_matches_waste_type(
        seller_product_seller_location: SellerProductSellerLocation,
        waste_type: WasteType,
    ):
        main_product_waste_types = MainProductWasteType.objects.filter(
            main_product=seller_product_seller_location.seller_product.product.main_product,
        )

        # Get Material Waste Types for the SellerProductSellerLocation.
        if main_product_waste_types.count() > 0 and hasattr(
            seller_product_seller_location, "material"
        ):
            material_waste_types = SellerProductSellerLocationMaterialWasteType.objects.filter(
                seller_product_seller_location_material=seller_product_seller_location.material
            )
        else:
            material_waste_types = None

        return main_product_waste_types.count() == 0 or (
            material_waste_types
            and material_waste_types.filter(
                main_product_waste_type__waste_type=waste_type,
            ).exists()
        )

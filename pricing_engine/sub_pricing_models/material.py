from typing import Optional

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.waste_type import WasteType
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class MaterialPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
        waste_type: Optional[WasteType],
    ) -> Optional[PricingLineItemGroup]:
        """
        This method computes the material price based on the SellerProductSellerLocation's
        (and related MainProduct) rental pricing structure.

        Each MainProduct, if it has Material, has a "included_tonnage_quantity" field that indicates
        quantity of tons for the selected Material.

        Returns:
          The material price (float)
        """
        if (
            seller_product_seller_location.seller_product.product.main_product.has_material
        ):
            included_tonnage_quantity = (
                seller_product_seller_location.seller_product.product.main_product.included_tonnage_quantity
            )
            if included_tonnage_quantity is None:
                included_tonnage_quantity = 2

            items: list[PricingLineItem]
            items = seller_product_seller_location.material.get_price(
                waste_type=waste_type,
                quantity=included_tonnage_quantity,
            )

            return (
                PricingLineItemGroup(
                    title="Material",
                    items=items,
                )
                if len(items) > 0
                else None
            )

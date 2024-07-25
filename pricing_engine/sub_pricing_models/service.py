from decimal import Decimal

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress


class ServicePrice:
    @staticmethod
    def get_price(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location: SellerProductSellerLocation,
    ):
        """
        This method computes the service price based on customer location,
        seller location, and product. You'll need to implement the logic here
        considering factors like distance, product complexity, etc.

        Args:
          user_address: Customer's address (UserAddress object)
          seller_product_seller_location: SellerProductSellerLocation object

        Returns:
          The service price (float)
        """
        return 0

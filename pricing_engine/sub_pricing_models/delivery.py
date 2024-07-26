from api.models.seller.seller_product_seller_location import SellerProductSellerLocation


class DeliveryPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
    ):
        return seller_product_seller_location.delivery_fee

from .add_on import AddOnAdmin
from .add_on_choice import AddOnChoiceAdmin
from .advertisement import AdvertisementAdmin
from .industry import IndustryAdmin
from .main_product import MainProductAdmin
from .main_product_category import MainProductCategoryAdmin
from .main_product_category_group import MainProductCategoryGroupAdmin
from .main_product_info import MainProductInfoAdmin
from .main_product_tag import MainProductTagAdmin
from .main_product_waste_type import MainProductWasteTypeAdmin
from .order import OrderAdmin
from .order_group import OrderGroupAdmin
from .order_group_material import OrderGroupMaterialAdmin
from .order_line_item_type import OrderLineItemTypeAdmin
from .order_review import OrderReviewAdmin
from .payout import PayoutAdmin
from .product import ProductAdmin
from .product_addon_choice import ProductAddOnChoiceAdmin
from .seller import SellerAdmin
from .seller_invoice_payable import SellerInvoicePayableAdmin
from .seller_invoice_payable_line_item import SellerInvoicePayableLineItemAdmin
from .seller_location import SellerLocationAdmin
from .seller_product import SellerProductAdmin
from .seller_product_seller_location import SellerProductSellerLocationAdmin
from .seller_product_seller_location_material import (
    SellerProductSellerLocationMaterialAdmin,
)

# from .seller_product_seller_location_material_waste_type import (
#     SellerProductSellerLocationMaterialWasteTypeAdmin,
# )
# from .seller_product_seller_location_rental import (
#     SellerProductSellerLocationRentalAdmin,
# )
from .seller_product_seller_location_rental_multi_step import (
    SellerProductSellerLocationRentalMultiStepAdmin,
)

# from .seller_product_seller_location_rental_one_step import (
#     SellerProductSellerLocationRentalOneStepAdmin,
# )
# from .seller_product_seller_location_service import (
#     SellerProductSellerLocationServiceAdmin,
# )
from .user import UserAdmin
from .user_address import UserAddressAdmin
from .user_group import UserGroupAdmin
from .user_group_credit_application import UserGroupCreditApplicationAdmin

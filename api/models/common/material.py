from api.models.waste_type import WasteType
from common.models import BaseModel
from pricing_engine.models.pricing_line_item import PricingLineItem


class PricingMaterial(BaseModel):
    class Meta:
        abstract = True

    def _is_complete(self):
        return len(self.waste_types.all()) > 0

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    def get_price(
        self,
        waste_type: WasteType,
        quantity: float,
    ) -> PricingLineItem:
        if self.waste_types.filter(
            main_product_waste_type__waste_type=waste_type
        ).exists():
            material_waste_type = self.waste_types.filter(
                main_product_waste_type__waste_type=waste_type
            ).first()

            return PricingLineItem(
                units="Tons",
                quantity=quantity,
                unit_price=material_waste_type.price_per_ton,
            )
        else:
            return None

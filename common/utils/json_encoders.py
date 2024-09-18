from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder


class DecimalFloatEncoder(DjangoJSONEncoder):
    """
    DecimalFloatEncoder is a DjangoJSONEncoder that encodes Decimal types as floats.
    """

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        else:
            return super().default(o)

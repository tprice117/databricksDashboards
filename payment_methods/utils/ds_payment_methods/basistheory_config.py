import basistheory
from django.conf import settings

api_client_use_pci = basistheory.ApiClient(
    basistheory.Configuration(
        api_key=settings.BASIS_THEORY_USE_PCI_API_KEY,
    )
)

api_client_management = basistheory.ApiClient(
    basistheory.Configuration(
        api_key=settings.BASIS_THEORY_MANGEMENT_API_KEY,
    )
)

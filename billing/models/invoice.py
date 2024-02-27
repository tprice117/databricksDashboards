from django.db import models

from api.models.main_product.add_on import AddOn
from common.models import BaseModel


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        OPEN = "open"
        PAID = "paid"
        VOID = "void"
        UNCOLLECTIBLE = "uncollectible"

    user_address = models.ForeignKey(
        "api.UserAddress",
        on_delete=models.CASCADE,
    )
    invoice_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe Invoice ID",
    )
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_remaining = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateTimeField(blank=True, null=True)
    hosted_invoice_url = models.URLField(blank=True, null=True)
    invoice_pdf = models.URLField(blank=True, null=True)
    metadata = models.JSONField()
    number = models.CharField(max_length=255, blank=True, null=True)
    paid = models.BooleanField()
    status = models.CharField(
        max_length=255,
        choices=Status.choices,
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.invoice_id

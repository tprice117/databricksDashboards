import uuid

from django.db import models
from django.db.models.signals import post_delete, pre_save

from api.models.payout import Payout
from api.models.seller.seller_location import SellerLocation
from common.models import BaseModel


class SellerInvoicePayable(BaseModel):
    STATUS_CHOICES = (
        ("UNPAID", "Unpaid"),
        ("ESCALATED", "Escalated"),
        ("ERROR", "Error"),
        ("READY_FOR_PAYOUT", "Ready for Payout"),
        ("PAID", "Paid"),
    )

    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    seller_location = models.ForeignKey(SellerLocation, models.PROTECT)
    invoice_file = models.FileField(upload_to=get_file_path, blank=True, null=True)
    supplier_invoice_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="UNPAID")

    def auto_delete_file_on_delete(sender, instance, **kwargs):
        """
        Deletes file from filesystem
        when corresponding `Payout` object is deleted.
        """
        if instance.invoice_file:
            instance.invoice_file.delete(save=False)

    def auto_delete_file_on_change(sender, instance, **kwargs):
        """
        Deletes old file from filesystem
        when corresponding `Payout` object is updated
        with new file.
        """
        if not instance.pk:
            return False

        try:
            old_file = Payout.objects.get(pk=instance.pk).invoice_file
            print(old_file)
        except Payout.DoesNotExist:
            return False

        new_file = instance.invoice_file
        if not old_file == new_file:
            old_file.delete(save=False)


pre_save.connect(
    SellerInvoicePayable.auto_delete_file_on_change, sender=SellerInvoicePayable
)
post_delete.connect(
    SellerInvoicePayable.auto_delete_file_on_delete, sender=SellerInvoicePayable
)

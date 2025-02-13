import uuid

from django.db import models
from django.forms import ValidationError

from common.models import BaseModel


class OrderGroupAttachment(BaseModel):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    def validate_file_extension(value):
        """
        Method to validate the file extension of the uploaded file.
        Currently only SVG files are unsupported.
        """
        if value.name.split(".")[-1] == "svg":
            raise ValidationError("Filetype not supported.")

    order_group = models.ForeignKey(
        "OrderGroup", on_delete=models.CASCADE, related_name="attachments"
    )

    file = models.FileField(
        upload_to=get_file_path, validators=[validate_file_extension]
    )

    def __str__(self):
        return self.file.name

    class Meta:
        verbose_name = "Booking Attachment"
        verbose_name_plural = "Booking Attachments"

    @property
    def file_type(self):
        return self.file.name.split(".")[-1]

    @property
    def file_name(self):
        return self.file.name

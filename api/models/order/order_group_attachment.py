import uuid
from django.db import models
from common.models import BaseModel


class OrderGroupAttachment(BaseModel):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    order_group = models.ForeignKey(
        "OrderGroup", on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=get_file_path)

    def __str__(self):
        return self.file.name

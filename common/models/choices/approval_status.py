from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    DECLINED = "DECLINED", "Declined"

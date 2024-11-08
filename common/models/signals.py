from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from common.middleware.save_author import get_request
from common.models import BaseModel


@receiver(pre_save)
def base_model_pre_save(sender, instance: BaseModel, **kwargs):
    # print("Running base_model_pre_save")
    # Sets the 'created_by' and 'updated_by' if 'sender' is a subclass of BaseModel
    if issubclass(sender, BaseModel):
        # Get current user via author backend.
        request = get_request()

        authenticated_user = None
        if hasattr(request, "auth"):
            authenticated_user = request.auth
        elif hasattr(request, "user"):
            authenticated_user = request.user

        # Set the 'updated_by' user.
        instance.updated_by = authenticated_user

        # If creating object, set the 'created_by' field.
        if (
            sender.objects.filter(pk=instance.pk).exists() is False
            and authenticated_user is not None
        ):
            instance.created_by = authenticated_user

        # Check if instance is Order instance(instance, Order)
        if hasattr(instance, "submitted_by") and hasattr(instance, "accepted_by"):
            # This is an Order instance
            if (
                instance.submitted_on is not None
                and instance.old_value("submitted_on") is None
            ):
                instance.submitted_by = authenticated_user
                # Sign rental agreement on checkout.
                instance.order_group.agreement_signed_by = authenticated_user
                instance.order_group.agreement_signed_on = timezone.now()
            old_status = instance.old_value("status")
            if old_status != instance.status:
                # Status changed
                if instance.status == instance.Status.SCHEDULED:
                    instance.accepted_by = authenticated_user
                    instance.accepted_on = timezone.now()
                elif instance.status == instance.Status.COMPLETE:
                    instance.completed_by = authenticated_user
                    instance.completed_on = timezone.now()
